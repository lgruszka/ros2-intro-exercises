#!/usr/bin/env python3
"""W8 - pick & place na Franka Research 3 (FR3) z moveit_py.

Sekwencja: ready -> pre-grasp nad klockiem -> zjazd -> chwyt -> ATTACH ->
podniesienie -> przeniesienie -> zjazd -> otwarcie -> DETACH -> odjazd w górę -> ready.

Uruchomienie (po `ros2 launch fr3_moveit pick_place.launch.py` w 1. terminalu):
    ros2 run fr3_moveit pick_place
Ten sam kod działa na fake hardware i na prawdziwym FR3 - różni się tylko launch.

Wzorzec: oficjalny tutorial MoveIt 2 "Motion Planning Python API".
"""
import os
import time

from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Pose, PoseStamped
from moveit.planning import MoveItPy
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_msgs.msg import AttachedCollisionObject, CollisionObject
from shape_msgs.msg import SolidPrimitive

EEF_LINK = 'fr3_link8'
BASE = 'fr3_link0'

# Pozycje sceny (m, względem bazy robota).
# Klocek 5 mm NAD blatem: po attach staje się częścią ROBOTA, a kontakt robot-stół
# to kolizja (stan startowy podniesienia byłby nieważny). Świat-świat nie koliduje,
# robot-świat tak - subtelna, ale kluczowa różnica.
KLOCEK_XYZ = (0.35, 0.25, 0.035)
CEL_XYZ = (0.35, -0.25, 0.035)
PREGRASP_Z = 0.25
# fr3_link8 -> czubki palców to ~0.10 m; przy 0.145 otwarte palce (rozstaw 7 cm)
# obejmują górną połowę klocka (4 cm szer.) bez kolizji, a dłoń zostaje ~2 cm nad nim.
GRASP_Z = 0.145
PLACE_Z = GRASP_Z + 0.015   # odkładanie: klocek ~1,5 cm nad blatem (bez kolizji z 'stol')


def build_config():
    """MoveItPy sam staje się 'move_groupem' - potrzebuje kompletu konfiguracji.

    URDF, SRDF, kinematyka i limity pochodzą z oficjalnych pakietów franka_ros2
    (te same pliki ładuje franka_fr3_moveit_config/launch/moveit.launch.py).
    Kontrolery i MoveItPy - z tego pakietu, OMPL - domyślna konfiguracja MoveIt.
    """
    bringup = get_package_share_directory('franka_bringup')
    description = get_package_share_directory('franka_description')
    fr3_cfg = get_package_share_directory('franka_fr3_moveit_config')
    return (
        MoveItConfigsBuilder(robot_name='fr3', package_name='fr3_moveit')
        .robot_description(file_path=os.path.join(bringup, 'urdf', 'franka_arm.urdf.xacro'),
                           mappings={'robot_type': 'fr3', 'hand': 'true', 'ee_id': 'franka_hand'})
        .robot_description_semantic(file_path=os.path.join(description, 'robots', 'fr3', 'fr3.srdf.xacro'),
                                    mappings={'hand': 'true', 'ee_id': 'franka_hand'})
        .robot_description_kinematics(file_path=os.path.join(fr3_cfg, 'config', 'kinematics.yaml'))
        .joint_limits(file_path=os.path.join(fr3_cfg, 'config', 'fr3_joint_limits.yaml'))
        .trajectory_execution(file_path='config/moveit_controllers.yaml')   # względem share/fr3_moveit
        .planning_pipelines(pipelines=['ompl'])
        .moveit_cpp(file_path='config/moveit_cpp.yaml')
        .to_moveit_configs()
    )


def plan_and_execute(robot, component, tries=3):
    """Plannery próbkujące bywają niedeterministyczne - do 3 prób (M9/W8)."""
    for i in range(tries):
        result = component.plan()
        if result:
            robot.execute(result.trajectory, controllers=[])
            return True
        print(f'  plan nieudany (próba {i + 1}/{tries}) - ponawiam', flush=True)
    return False


def goto_named(robot, arm, name):
    arm.set_start_state_to_current_state()
    arm.set_goal_state(configuration_name=name)
    return plan_and_execute(robot, arm)


def goto_pose(robot, arm, x, y, z):
    goal = PoseStamped()
    goal.header.frame_id = BASE
    goal.pose.position.x, goal.pose.position.y, goal.pose.position.z = x, y, z
    # Chwytak w dół (180° wokół X) + obrót o 45° wokół osi Z: fr3_hand jest na
    # fr3_link8 obrócony o -45° (fr3_hand_joint), więc sama orientacja (x=1, w=0)
    # ustawiłaby palce pod 45° do ścian klocka. Ten kwaternion daje palce równoległe
    # do ścian klocka (kwaternion jest dla fr3_link8, bo tego linku dotyczy cel).
    goal.pose.orientation.x = 0.9239
    goal.pose.orientation.y = -0.3827
    goal.pose.orientation.z = 0.0
    goal.pose.orientation.w = 0.0
    arm.set_start_state_to_current_state()
    arm.set_goal_state(pose_stamped_msg=goal, pose_link=EEF_LINK)
    return plan_and_execute(robot, arm)


def gripper(robot, hand, state):     # state: 'open' | 'close'
    hand.set_start_state_to_current_state()
    hand.set_goal_state(configuration_name=state)
    return plan_and_execute(robot, hand)


def add_box(psm, name, size, xyz):
    co = CollisionObject()
    co.header.frame_id = BASE
    co.id = name
    co.primitives.append(SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(size)))
    pose = Pose()
    pose.position.x, pose.position.y, pose.position.z = xyz
    co.primitive_poses.append(pose)
    co.operation = CollisionObject.ADD
    with psm.read_write() as scene:
        scene.apply_collision_object(co)
        scene.current_state.update()


def set_attached(psm, obj_id, attach):
    """Attach/detach: klocek staje się (przestaje być) częścią robota w scenie."""
    aco = AttachedCollisionObject()
    aco.link_name = 'fr3_hand'
    aco.object.id = obj_id
    aco.object.operation = CollisionObject.ADD if attach else CollisionObject.REMOVE
    aco.touch_links = ['fr3_hand', 'fr3_leftfinger', 'fr3_rightfinger']
    with psm.read_write() as scene:
        scene.process_attached_collision_object(aco)
        scene.current_state.update()


def main():
    config = build_config()
    fr3 = MoveItPy(node_name='pick_place', config_dict=config.to_dict())
    arm = fr3.get_planning_component('fr3_arm')
    hand = fr3.get_planning_component('fr3_hand')
    psm = fr3.get_planning_scene_monitor()
    time.sleep(2.0)  # daj scenie zassać pierwszy /joint_states

    print('1/8 scena: stół + klocek', flush=True)
    add_box(psm, 'stol', (0.8, 0.9, 0.05), (0.4, 0.0, -0.025))
    add_box(psm, 'klocek', (0.04, 0.04, 0.06), KLOCEK_XYZ)

    print('2/8 ready + otwarcie chwytaka', flush=True)   # otwarte palce PRZED zjazdem - zamknięte
    assert goto_named(fr3, arm, 'ready')     # to zwarta bryła, która koliduje z klockiem
    assert gripper(fr3, hand, 'open')
    print('3/8 pre-grasp', flush=True)
    assert goto_pose(fr3, arm, KLOCEK_XYZ[0], KLOCEK_XYZ[1], PREGRASP_Z)
    print('4/8 zjazd (otwarte palce obejmują klocek)', flush=True)
    assert goto_pose(fr3, arm, KLOCEK_XYZ[0], KLOCEK_XYZ[1], GRASP_Z)
    # ATTACH PRZED close: attach wpisuje klocek do ACM (touch_links), więc plan domknięcia
    # palców NA klocku nie jest już „kolizją". (Na prawdziwym FR3 palce i tak zaciskają się
    # fizycznie - attach to deklaracja dla sceny, nie dla sprzętu.)
    print('5/8 attach + chwyt', flush=True)
    set_attached(psm, 'klocek', attach=True)
    assert gripper(fr3, hand, 'close')
    print('6/8 podnieś i przenieś', flush=True)
    assert goto_pose(fr3, arm, KLOCEK_XYZ[0], KLOCEK_XYZ[1], PREGRASP_Z)
    assert goto_pose(fr3, arm, CEL_XYZ[0], CEL_XYZ[1], PREGRASP_Z)
    print('7/8 odłóż', flush=True)
    assert goto_pose(fr3, arm, CEL_XYZ[0], CEL_XYZ[1], PLACE_Z)
    assert gripper(fr3, hand, 'open')
    set_attached(psm, 'klocek', attach=False)
    # odjazd pionowo w górę PRZED 'ready': prosto z PLACE_Z palce potrafią zahaczyć o odłożony
    # klocek i MoveIt odrzuca plan („Found a contact between 'klocek' and 'fr3_rightfinger'”)
    print('8/8 odjazd w górę i powrót do ready', flush=True)
    assert goto_pose(fr3, arm, CEL_XYZ[0], CEL_XYZ[1], PREGRASP_Z)
    assert goto_named(fr3, arm, 'ready')
    print('✓ pick & place zakończony', flush=True)
    fr3.shutdown()


if __name__ == '__main__':
    main()
