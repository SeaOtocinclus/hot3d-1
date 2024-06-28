# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import unittest
from pathlib import Path

from data_loaders.AriaDataProvider import AriaDataProvider
from data_loaders.PathProvider import Hot3dDataPathProvider
from projectaria_tools.core.calibration import FISHEYE624, LINEAR
from projectaria_tools.core.stream_id import StreamId


try:
    from libfb.py import parutil

    data_path = Path(parutil.get_file_path("test_data/", pkg=__package__))
except ImportError:

    data_path = Path(__file__).parent

sequence_path = data_path / "data_sample/Aria/P0003_c701bd11"
vrs_file_filepath = str(sequence_path / "recording.vrs")


class TestAriaDataProvider(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()

    def test_provider_aria_recording_with_mps(self) -> None:
        path_provider = Hot3dDataPathProvider.fromRecordingFolder(
            recording_instance_folderpath=sequence_path
        )
        self.assertTrue(os.path.exists(path_provider.vrs_filepath))
        self.assertTrue(os.path.exists(path_provider.mps_folderpath))
        provider = AriaDataProvider(
            path_provider.vrs_filepath,
            path_provider.mps_folderpath,
        )

        #
        # Test MPS data retrieval
        #

        # Global point cloud
        point_cloud = provider.get_point_cloud()
        self.assertIsNotNone(point_cloud)
        self.assertGreater(len(point_cloud), 0)

        # Eye Gaze (that is temporal data)
        timestamps = provider.get_sequence_timestamps()
        self.assertTrue(len(timestamps) > 0)

        eye_gaze = provider.get_eye_gaze(timestamps[0])
        self.assertIsNotNone(eye_gaze)

    def test_provider_aria_recording(self) -> None:
        self.assertTrue(os.path.exists(vrs_file_filepath))
        provider = AriaDataProvider(vrs_file_filepath, "")

        self.assertIsNotNone(provider)
        self.assertIsNotNone(provider.get_device_calibration())

        # Aria VRS files contains 3 Image streams (1 RGB, 2 SLAM)
        stream_ids = provider.get_image_stream_ids()
        self.assertEqual(len(stream_ids), 3)
        self.assertTrue(StreamId("214-1") in stream_ids)
        self.assertTrue(StreamId("1201-1") in stream_ids)
        self.assertTrue(StreamId("1201-2") in stream_ids)

        timestamps = provider.get_sequence_timestamps()
        self.assertTrue(len(timestamps) > 0)

        for stream_id in stream_ids:
            img_array = provider.get_image(timestamps[0], stream_id)
            self.assertIsNotNone(img_array)
            if "rgb" in provider.get_image_stream_label(stream_id):
                self.assertEqual(img_array.shape, (1408, 1408, 3))
            elif "slam" in provider.get_image_stream_label(stream_id):
                self.assertEqual(img_array.shape, (480, 640))

            undistorted_img_array = provider.get_image(timestamps[0], stream_id)
            self.assertIsNotNone(undistorted_img_array)

            # Retrieve camera calibration
            self.assertIsNotNone(provider.get_camera_calibration(stream_id))
            self.assertIsNotNone(provider.get_camera_calibration(stream_id, FISHEYE624))
            self.assertIsNotNone(provider.get_camera_calibration(stream_id, LINEAR))

            # Assert we have the right camera type
            self.assertEqual(
                provider.get_camera_calibration(stream_id)[1].model_name(),
                FISHEYE624,
            )
            self.assertEqual(
                provider.get_camera_calibration(stream_id, LINEAR)[1].model_name(),
                LINEAR,
            )

        # MPS resources are empty since not initialized
        self.assertIsNone(provider.get_point_cloud())
