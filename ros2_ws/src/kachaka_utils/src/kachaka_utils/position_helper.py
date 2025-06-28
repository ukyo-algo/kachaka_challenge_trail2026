from geometry_msgs.msg import PoseStamped

def get_named_pose(name: str) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = "map"
    pose.header.stamp.sec = 0  # nav2が必要な場合はTime.nowで補完

    if name == "host_room":
        pose.pose.position.x = 1.23
        pose.pose.position.y = 2.34
        pose.pose.orientation.z = 0.707
        pose.pose.orientation.w = 0.707
    elif name == "entrance":
        pose.pose.position.x = -0.5
        pose.pose.position.y = 1.8
        pose.pose.orientation.w = 1.0
    else:
        raise ValueError(f"Unknown location: {name}")
    
    return pose