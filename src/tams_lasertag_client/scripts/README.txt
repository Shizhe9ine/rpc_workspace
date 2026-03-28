
STRATEGY==================================

We start at a point in the furthermost left room, and cycle through all of the rooms. In the bigger ones the robot will drive in a circle to "see" everything

I have written a path that doesnt go to rooms that might be locked while youre working on it. (mission_loop_test, its currently commented out of the node)

nav2 runs smoothly for me

ISSUES====================================

rviz regularly crashes

demo.py receives images while lasertag_strats.py doesnt. 
(lasertag.py is supposed to filter out images that do not contain an apriltag and only send ones that do)

TODO!!===================================
make a proper filter for received images with apriltag, only send pictures that would heed points

test lasertag_strats, you can ask sam to turn on a game server
- does the cycling through the rooms work?(use testing locations if the other rooms are locked )
- does the node pass on its image exactly when an apriltag is properly in view?

OPTIONAL================================
make the robot take a zigzag shaped path in the hallway (between points -3.53,4.54 and -4.44,1.03), to make it harder for opposing robots to capture a high scoring image

"pursuit" option: when detecting a far away apriltag, move closer before taking the picture to score higher

DONT FORGET=============================
ssh @ubuntu
source rpc_workspace/install/setup.bash
dont colcon build in a shell




