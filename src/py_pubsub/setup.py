from setuptools import find_packages, setup

package_name = "py_pubsub"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            "share/" + package_name + "/config",
            ["config/tams_floor.yaml", "config/tams_floor.pgm"],
        ),
        ("share/" + package_name + "/launch", ["launch/main.launch"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="tams",
    maintainer_email="tams@todo.todo",
    description="draws house",
    license="Apache-2.0",
    extras_require={
        "test": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "talker = py_pubsub.publisher_member_function:main",
            "listener = py_pubsub.subscriber_member_function:main",
            "move= py_pubsub.move_function:main",  # assigment 2.3 moving funtion
            "detect = py_pubsub.obstacle_detection_function:main",  # assigment 2.4 moving with obstacle detection
            "auto = py_pubsub.move_action_client:main",  # assignment 3 move between 2 points
        ],
    },
)
