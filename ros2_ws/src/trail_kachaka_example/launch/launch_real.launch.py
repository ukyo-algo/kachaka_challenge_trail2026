# Copyright (C) 2023 Kachaka

import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # Get directories
    nav2_dir = get_package_share_directory('kachaka_nav2_bringup')
    
    # Create launch configuration variables
    namespace = LaunchConfiguration('namespace', default='')
    
    # Declare launch arguments
    declare_namespace_cmd = DeclareLaunchArgument(
        'namespace',
        default_value=namespace,
        description='Top-level namespace'
    )
    
    # Function to resolve paths with the map name
    def get_paths_and_launch(context):        
        # Include localization launch file
        localization_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_dir, 'launch', 'localization_launch.py')
            ),
            launch_arguments={
                'use_sim_time': 'false',
                'namespace': namespace,
                'map': '',
            }.items()
        )

        # Include navigation launch file
        navigation_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(nav2_dir, 'launch', 'navigation_launch.py')
            ),
            launch_arguments={
                'use_sim_time': 'false',
                'namespace': namespace,
                'autostart': 'true',
                'params_file': os.path.join(nav2_dir, 'params', 'nav2_params.yaml'),
            }.items()
        )
        
        return [localization_launch, navigation_launch]
    
    # Create and return launch description
    ld = LaunchDescription()
    
    # Add declared arguments
    ld.add_action(declare_namespace_cmd)
    
    # Add the actions to launch simulation and localization using OpaqueFunction
    ld.add_action(OpaqueFunction(function=get_paths_and_launch))
    
    return ld
