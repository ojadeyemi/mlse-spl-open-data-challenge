import json

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter, FuncAnimation
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Line3D

# Default connections between joints. Change these as you please
connections = [
    ("R_EYE", "L_EYE"),
    ("R_EYE", "NOSE"),
    ("L_EYE", "NOSE"),
    ("R_EYE", "R_EAR"),
    ("L_EYE", "L_EAR"),
    ("R_SHOULDER", "L_SHOULDER"),
    ("R_SHOULDER", "R_ELBOW"),
    ("L_SHOULDER", "L_ELBOW"),
    ("R_ELBOW", "R_WRIST"),
    ("L_ELBOW", "L_WRIST"),
    ("R_SHOULDER", "R_HIP"),
    ("L_SHOULDER", "L_HIP"),
    ("R_HIP", "L_HIP"),
    ("R_HIP", "R_KNEE"),
    ("L_HIP", "L_KNEE"),
    ("R_KNEE", "R_ANKLE"),
    ("L_KNEE", "L_ANKLE"),
    ("R_WRIST", "R_1STFINGER"),
    ("R_WRIST", "R_5THFINGER"),
    ("L_WRIST", "L_1STFINGER"),
    ("L_WRIST", "L_5THFINGER"),
    ("R_ANKLE", "R_1STTOE"),
    ("R_ANKLE", "R_5THTOE"),
    ("L_ANKLE", "L_1STTOE"),
    ("L_ANKLE", "L_5THTOE"),
    ("R_ANKLE", "R_CALC"),
    ("L_ANKLE", "L_CALC"),
    ("R_1STTOE", "R_5THTOE"),
    ("L_1STTOE", "L_5THTOE"),
    ("R_1STTOE", "R_CALC"),
    ("L_1STTOE", "L_CALC"),
    ("R_5THTOE", "R_CALC"),
    ("L_5THTOE", "L_CALC"),
    ("R_1STFINGER", "R_5THFINGER"),
    ("L_1STFINGER", "L_5THFINGER"),
    ("R_1STFINGER", "R_5THFINGER"),
    ("L_1STFINGER", "L_5THFINGER"),
]


def animate_trial(
    path_to_json: str,
    connections: list[tuple[str, str]] = connections,
    xbuffer=4.0,
    ybuffer=4.0,
    zlim=8.0,
    elev=15.0,
    azim=40.0,
    player_color="purple",
    player_lw=2,
    ball_color="#ee6730",
    ball_size=20.0,
    show_court=True,
    notebook_mode=True,
):
    """
    Function to animate a single trial of 3D pose data.

    Parameters:
    -----------
    - path_to_json: str
        The path to the JSON file containing the 3D pose data.
    - connections: list of tuples
        A list of tuples, where each tuple contains two strings representing the joints to connect.
    - xbuffer: float
        The buffer to add to the x-axis limits.
    - ybuffer: float
        The buffer to add to the y-axis limits.
    - zlim: float
        The limit for the z-axis height.
    - elev: float
        The elevation angle for the 3D plot.
    - azim: float
        The azimuth angle for the 3D plot.
    - player_color: str
        The color to use for the player lines.
    - player_lw: float
        The line width to use for the player lines.
    - ball_color: str
        The color to use for the ball.
    - ball_size: float
        The size to use for the ball.
    - show_court: bool
        Whether to show the basketball court in the background.
    - notebook_mode: bool
        Whether function is used within a Jupyter notebook.

    Returns:
    --------
    - anim: matplotlib.animation.FuncAnimation
        The animation object created by the function.
    """

    if notebook_mode:
        plt.rcParams["animation.html"] = "jshtml"

    if show_court:
        try:
            from mplbasketball.court3d import draw_court_3d
        except ModuleNotFoundError:
            print("mplbasketball not installed. Cannot show court.")
            show_court = False

    with open(path_to_json, "r") as f:
        data = json.load(f)

    player_joint_dict = {}
    ball_data_array = []

    N_frames = len(data["tracking"])

    # The block of code below returns a dictionary, where each key is a 3D time series for coordinates of a joint.
    # Note that it is a list of N_frames elements, each of which is a 3-element list.
    # If you want to use numpy, you will have to cast it into a numpy array.
    for frame_data in data["tracking"]:
        for joint in frame_data["data"]["player"]:
            if joint not in player_joint_dict:
                player_joint_dict[joint] = []
            player_joint_dict[joint].append(frame_data["data"]["player"][joint])
        ball_data_array.append(frame_data["data"]["ball"])

    # For convenience, we will cast everything to numpy arrays here, but you can keep them as lists if you prefer.
    for joint in player_joint_dict:
        player_joint_dict[joint] = np.array(player_joint_dict[joint])
    ball_data_array = np.array(ball_data_array)

    # Animate the data
    fig = plt.figure(figsize=(8, 8))
    ax: Axes3D = fig.add_subplot(111, projection="3d")
    # Set up initial plot properties
    ax.set_zlim([0, zlim])
    ax.set_box_aspect([1, 1, 1])
    ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.view_init(elev=elev, azim=azim)

    # Prepare the lines to be updated
    lines: dict[tuple[str, str], Line3D] = {
        connection: ax.plot([], [], [], c=player_color, lw=player_lw)[0] for connection in connections
    }

    ball: Line3D
    (ball,) = ax.plot([], [], [], "o", markersize=ball_size, c=ball_color)

    elbow_dev_line: Line3D
    (elbow_dev_line,) = ax.plot([], [], [], c="red", lw=1)

    wrist_dev_line: Line3D
    (wrist_dev_line,) = ax.plot([], [], [], c="green", lw=1)

    hand_dev_line: Line3D
    (hand_dev_line,) = ax.plot([], [], [], c="blue", lw=1)

    # Initialize the planes as None
    sagittal_plane = [None]  # Use a list to make it mutable in the nested function
    coronal_plane = [None]

    def update(frame: int):
        nonlocal sagittal_plane, coronal_plane

        # Use the average of the right and left hip to center the view.
        rh_xy = player_joint_dict["R_HIP"][frame][:2]
        lh_xy = player_joint_dict["L_HIP"][frame][:2]
        mh_xy = (rh_xy + lh_xy) / 2

        ax.set_xlim([mh_xy[0] - xbuffer, mh_xy[0] + xbuffer])
        ax.set_ylim([mh_xy[1] - ybuffer, mh_xy[1] + ybuffer])

        # Update the line data for each connection
        for connection in connections:
            part1, part2 = connection
            x = [
                player_joint_dict[part1][frame, 0],
                player_joint_dict[part2][frame, 0],
            ]
            y = [
                player_joint_dict[part1][frame, 1],
                player_joint_dict[part2][frame, 1],
            ]
            z = [
                player_joint_dict[part1][frame, 2],
                player_joint_dict[part2][frame, 2],
            ]
            lines[connection].set_data_3d(x, y, z)

        # Update ball data
        x = ball_data_array[frame, 0]
        y = ball_data_array[frame, 1]
        z = ball_data_array[frame, 2]
        ball.set_data_3d([x], [y], [z])

        # Calculate additional points for analysis
        r_shoulder = player_joint_dict["R_SHOULDER"][frame]
        l_shoulder = player_joint_dict["L_SHOULDER"][frame]
        r_elbow = player_joint_dict["R_ELBOW"][frame]
        r_wrist = player_joint_dict["R_WRIST"][frame]
        r_hand = np.mean([player_joint_dict["R_1STFINGER"][frame], player_joint_dict["R_5THFINGER"][frame]], axis=0)

        # Calculate midline (between shoulders)
        shoulder_midpoint = (r_shoulder + l_shoulder) / 2

        # Define variables for the coordinates to update deviation lines
        elbow_dev_x = [shoulder_midpoint[0], r_elbow[0]]
        elbow_dev_y = [shoulder_midpoint[1], r_elbow[1]]
        elbow_dev_z = [shoulder_midpoint[2], r_elbow[2]]

        wrist_dev_x = [shoulder_midpoint[0], r_wrist[0]]
        wrist_dev_y = [shoulder_midpoint[1], r_wrist[1]]
        wrist_dev_z = [shoulder_midpoint[2], r_wrist[2]]

        hand_dev_x = [shoulder_midpoint[0], r_hand[0]]
        hand_dev_y = [shoulder_midpoint[1], r_hand[1]]
        hand_dev_z = [shoulder_midpoint[2], r_hand[2]]

        # Update deviation lines
        elbow_dev_line.set_data_3d(elbow_dev_x, elbow_dev_y, elbow_dev_z)
        wrist_dev_line.set_data_3d(wrist_dev_x, wrist_dev_y, wrist_dev_z)
        hand_dev_line.set_data_3d(hand_dev_x, hand_dev_y, hand_dev_z)

        # Remove previous planes if they exist
        if sagittal_plane[0] is not None:
            sagittal_plane[0].remove()
        if coronal_plane[0] is not None:
            coronal_plane[0].remove()

        # Define the sagittal plane at x = shoulder_midpoint[0]
        x_plane = shoulder_midpoint[0]
        y_min = mh_xy[1] - ybuffer
        y_max = mh_xy[1] + ybuffer
        z_min = 0
        z_max = zlim
        y_plane = np.linspace(y_min, y_max, num=10)
        z_plane = np.linspace(z_min, z_max, num=10)
        Y_plane, Z_plane = np.meshgrid(y_plane, z_plane)
        X_plane = np.full_like(Y_plane, fill_value=x_plane)

        # Plot the sagittal plane
        sagittal_plane[0] = ax.plot_surface(X_plane, Y_plane, Z_plane, color="gray", alpha=0.3, edgecolor="none")

        # Define the coronal plane at y = shoulder_midpoint[1]
        y_plane_coronal = shoulder_midpoint[1]
        x_min = mh_xy[0] - xbuffer
        x_max = mh_xy[0] + xbuffer
        x_plane_coronal = np.linspace(x_min, x_max, num=10)
        z_plane_coronal = np.linspace(z_min, z_max, num=10)
        X_plane_coronal, Z_plane_coronal = np.meshgrid(x_plane_coronal, z_plane_coronal)
        Y_plane_coronal = np.full_like(X_plane_coronal, fill_value=y_plane_coronal)

        # Plot the coronal plane
        coronal_plane[0] = ax.plot_surface(
            X_plane_coronal, Y_plane_coronal, Z_plane_coronal, color="blue", alpha=0.3, edgecolor="none"
        )

    if show_court is True:
        ax.grid(False)
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
        ax.xaxis.pane.set_edgecolor("w")
        ax.yaxis.pane.set_edgecolor("w")
        ax.zaxis.pane.set_edgecolor("w")
        ax.xaxis.line.set_linewidth(0)
        ax.yaxis.line.set_linewidth(0)
        ax.zaxis.line.set_linewidth(0)
        draw_court_3d(ax, origin=np.array([0.0, 0.0]), line_width=2)

    plt.subplots(layout="constrained")
    plt.close()

    anim = FuncAnimation(fig, update, frames=N_frames, interval=1000 / 30)
    write = FFMpegWriter(fps=60)

    anim.save("SaggitalAndCoronalPlanes.mp4", writer=write)
    return anim
