"""
Simple centroid-based face tracker.

Maintains identity of detected faces across consecutive video frames
by matching face bounding box centers using spatial proximity.

This is NOT a re-identification model. It assumes:
- Faces don't teleport across the frame between consecutive samples
- The sampling rate is high enough that face positions change gradually

Limitations:
- Will lose track if a face disappears and reappears after many frames
- May confuse identities if two faces cross paths
- No appearance-based matching (a face is just a position)
"""

from dataclasses import dataclass, field

import numpy as np

from app.pipeline.face_detector import DetectedFace


@dataclass
class TrackedFace:
    """A face being tracked across frames."""
    track_id: int
    last_center_x: float
    last_center_y: float
    frame_count: int = 1
    first_seen_sec: float = 0.0
    last_seen_sec: float = 0.0


class FaceTracker:
    """
    Tracks faces across video frames using centroid proximity.

    Args:
        max_distance: Maximum normalized distance (0-1) between centroids
                     to consider them the same face. Default 0.15 means
                     a face must move less than 15% of the frame width
                     between consecutive samples.
        max_missing_frames: How many consecutive frames a face can be
                           missing before its track is dropped.
    """

    def __init__(
        self,
        max_distance: float = 0.15,
        max_missing_frames: int = 10,
    ):
        self.max_distance = max_distance
        self.max_missing_frames = max_missing_frames
        self._tracks: dict[int, TrackedFace] = {}
        self._next_id = 1
        self._missing_counts: dict[int, int] = {}

    def update(
        self, faces: list[DetectedFace], timestamp_sec: float
    ) -> dict[int, DetectedFace]:
        """
        Match detected faces to existing tracks.

        Args:
            faces: List of faces detected in the current frame.
            timestamp_sec: Current timestamp in the video.

        Returns:
            Mapping of track_id → DetectedFace for this frame.
        """
        if not faces:
            # Increment missing count for all tracks
            for tid in list(self._missing_counts):
                self._missing_counts[tid] += 1
            self._prune_stale_tracks()
            return {}

        # Compute centers for current detections
        centers = np.array([
            [f.bbox.center_x, f.bbox.center_y] for f in faces
        ])

        assignments: dict[int, DetectedFace] = {}
        used_detections = set()
        used_tracks = set()

        if self._tracks:
            # Build cost matrix: distance between each track and each detection
            track_ids = list(self._tracks.keys())
            track_centers = np.array([
                [self._tracks[tid].last_center_x, self._tracks[tid].last_center_y]
                for tid in track_ids
            ])

            # Compute pairwise distances
            distances = np.linalg.norm(
                track_centers[:, np.newaxis, :] - centers[np.newaxis, :, :],
                axis=2,
            )

            # Greedy assignment: closest pairs first
            while True:
                if distances.size == 0:
                    break
                min_idx = np.unravel_index(np.argmin(distances), distances.shape)
                min_dist = distances[min_idx]

                if min_dist > self.max_distance:
                    break

                t_idx, d_idx = min_idx
                tid = track_ids[t_idx]

                if tid not in used_tracks and d_idx not in used_detections:
                    assignments[tid] = faces[d_idx]
                    used_tracks.add(tid)
                    used_detections.add(d_idx)

                    # Update track
                    self._tracks[tid].last_center_x = centers[d_idx][0]
                    self._tracks[tid].last_center_y = centers[d_idx][1]
                    self._tracks[tid].frame_count += 1
                    self._tracks[tid].last_seen_sec = timestamp_sec
                    self._missing_counts[tid] = 0

                # Mark this pair as processed
                distances[t_idx, d_idx] = float("inf")

        # Create new tracks for unmatched detections
        for i, face in enumerate(faces):
            if i not in used_detections:
                tid = self._next_id
                self._next_id += 1
                self._tracks[tid] = TrackedFace(
                    track_id=tid,
                    last_center_x=centers[i][0],
                    last_center_y=centers[i][1],
                    first_seen_sec=timestamp_sec,
                    last_seen_sec=timestamp_sec,
                )
                self._missing_counts[tid] = 0
                assignments[tid] = face

        # Increment missing count for unmatched tracks
        for tid in self._tracks:
            if tid not in used_tracks and tid not in assignments:
                self._missing_counts[tid] = self._missing_counts.get(tid, 0) + 1

        self._prune_stale_tracks()
        return assignments

    def _prune_stale_tracks(self):
        """Remove tracks that haven't been seen for too long."""
        stale = [
            tid for tid, count in self._missing_counts.items()
            if count > self.max_missing_frames
        ]
        for tid in stale:
            del self._tracks[tid]
            del self._missing_counts[tid]

    def get_all_tracks(self) -> dict[int, TrackedFace]:
        """Return all current tracks (including stale ones not yet pruned)."""
        return dict(self._tracks)
