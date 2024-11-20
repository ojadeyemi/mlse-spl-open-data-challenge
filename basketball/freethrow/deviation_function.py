import json
from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class FreeThrowDataLoader:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def load_participant_data(self, participant_id: str) -> List[Dict]:
        participant_path = self.base_path / participant_id
        trials = []

        for trial_file in sorted(participant_path.glob("BB_FT_*.json")):
            with open(trial_file, "r") as f:
                trial_data = json.load(f)
                trials.append(trial_data)

        return trials


class FreeThrowAnalyzer:
    def __init__(self, trials_data: List[Dict]):
        self.trials_data = trials_data
        self.participant_id = trials_data[0]["participant_id"]

    def _calculate_midpoint(self, p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
        return (p1 + p2) / 2

    def analyze_trial(self, trial_data: Dict) -> Dict[str, Any]:
        frames_analysis = []

        for frame in trial_data["tracking"]:
            player = frame["data"]["player"]

            r_shoulder = np.array(player["R_SHOULDER"])
            l_shoulder = np.array(player["L_SHOULDER"])
            r_elbow = np.array(player["R_ELBOW"])
            r_wrist = np.array(player["R_WRIST"])
            r_hand = np.mean([np.array(player["R_1STFINGER"]), np.array(player["R_5THFINGER"])], axis=0)

            shoulder_midpoint = self._calculate_midpoint(r_shoulder, l_shoulder)

            elbow_dev = np.linalg.norm(r_elbow - shoulder_midpoint)
            wrist_dev = np.linalg.norm(r_wrist - shoulder_midpoint)
            hand_dev = np.linalg.norm(r_hand - shoulder_midpoint)

            elbow_shoulder_dist = np.linalg.norm(r_elbow - r_shoulder)
            wrist_shoulder_dist = np.linalg.norm(r_wrist - r_shoulder)
            hand_shoulder_dist = np.linalg.norm(r_hand - r_shoulder)

            frames_analysis.append(
                {
                    "frame": frame["frame"],
                    "time": frame["time"],
                    "elbow_deviation": elbow_dev,
                    "wrist_deviation": wrist_dev,
                    "hand_deviation": hand_dev,
                    "elbow_shoulder_dist": elbow_shoulder_dist,
                    "wrist_shoulder_dist": wrist_shoulder_dist,
                    "hand_shoulder_dist": hand_shoulder_dist,
                }
            )

        return {"trial_id": trial_data["trial_id"], "result": trial_data["result"], "frames_analysis": frames_analysis}

    def analyze_all_trials(self) -> pd.DataFrame:
        trials_summary = []

        for trial_idx, trial in enumerate(self.trials_data, 1):
            analysis = self.analyze_trial(trial)
            frames_df = pd.DataFrame(analysis["frames_analysis"])

            trials_summary.append(
                {
                    "trial_number": trial_idx,
                    "trial_id": trial["trial_id"],
                    "result": analysis["result"],
                    "max_elbow_deviation": frames_df["elbow_deviation"].max(),
                    "max_wrist_deviation": frames_df["wrist_deviation"].max(),
                    "max_hand_deviation": frames_df["hand_deviation"].max(),
                    "avg_elbow_deviation": frames_df["elbow_deviation"].mean(),
                    "avg_wrist_deviation": frames_df["wrist_deviation"].mean(),
                    "avg_hand_deviation": frames_df["hand_deviation"].mean(),
                    "std_elbow_deviation": frames_df["elbow_deviation"].std(),
                    "std_wrist_deviation": frames_df["wrist_deviation"].std(),
                    "std_hand_deviation": frames_df["hand_deviation"].std(),
                }
            )

        return pd.DataFrame(trials_summary)

    def check_results_distribution(self):
        trials_df = self.analyze_all_trials()
        result_counts = trials_df["result"].value_counts()
        print("Distribution of Results (Make vs. Miss):")
        print(result_counts)

    def plot_deviation_spread(self):
        trials_df = self.analyze_all_trials()

        # Separate makes and misses
        makes = trials_df[trials_df["result"] == "made"]
        misses = trials_df[trials_df["result"] == "missed"]

        # Create subplots
        fig, axs = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

        # Plot makes
        if not makes.empty:
            axs[0].plot(makes["trial_number"], makes["std_elbow_deviation"], "o-", label="Elbow Deviation")
            axs[0].plot(makes["trial_number"], makes["std_wrist_deviation"], "o-", label="Wrist Deviation")
            axs[0].plot(makes["trial_number"], makes["std_hand_deviation"], "o-", label="Hand Deviation")
            axs[0].set_title("Spread of Deviations - Made Shots")
            axs[0].set_xlabel("Trial Number")
            axs[0].set_ylabel("Standard Deviation of Deviation (meters)")
            axs[0].legend()
        else:
            axs[0].text(
                0.5,
                0.5,
                "No made shots in the dataset.",
                horizontalalignment="center",
                verticalalignment="center",
                transform=axs[0].transAxes,
            )
            axs[0].set_title("Spread of Deviations - Made Shots")
            axs[0].set_xlabel("Trial Number")
            axs[0].set_ylabel("Standard Deviation of Deviation (meters)")

        # Plot misses
        if not misses.empty:
            axs[1].plot(misses["trial_number"], misses["std_elbow_deviation"], "s-", label="Elbow Deviation")
            axs[1].plot(misses["trial_number"], misses["std_wrist_deviation"], "s-", label="Wrist Deviation")
            axs[1].plot(misses["trial_number"], misses["std_hand_deviation"], "s-", label="Hand Deviation")
            axs[1].set_title("Spread of Deviations - Missed Shots")
            axs[1].set_xlabel("Trial Number")
            axs[1].legend()
        else:
            axs[1].text(
                0.5,
                0.5,
                "No missed shots in the dataset.",
                horizontalalignment="center",
                verticalalignment="center",
                transform=axs[1].transAxes,
            )
            axs[1].set_title("Spread of Deviations - Missed Shots")
            axs[1].set_xlabel("Trial Number")

        plt.tight_layout()
        plt.show()
