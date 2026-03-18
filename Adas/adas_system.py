import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
from collections import deque
import math
from enum import Enum
from datetime import datetime


class VehicleType(Enum):
    CAR = "car"
    TRUCK = "truck"
    BUS = "bus"

@dataclass
class Vehicle:
    vehicle_id: int
    vehicle_type: VehicleType
    trajectory: deque
    center: Tuple[float, float]
    bbox: Tuple[int, int, int, int]
    speed: float
    distance: float
    is_high_beam_on: bool
    lane:str="unknown"
    def get_trajectory_points(self):
        return list(self.trajectory)
    def predict_position(self, frames=10):
        if len(self.trajectory) < 2:
            return self.center

        x1,y1 = self.trajectory[-2]
        x2,y2 = self.trajectory[-1]

        dx = x2-x1
        dy = y2-y1

        return (x2 + dx*frames, y2 + dy*frames)

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class Alert:
    level: AlertLevel
    title: str
    message: str
    recommendation: str
    timestamp: datetime
    duration: int = 5  # seconds
    def is_expired(self, current_time: datetime) -> bool:
        """Check if alert has expired"""
        elapsed = (current_time - self.timestamp).total_seconds()
        return elapsed > self.duration


class DetectVehicle:
    def __init__(self):
        self.vehicle_type = None
        self.truck_size_threshold = 5000
        self.vehicle_counter = 0
        self.vehicle: List = []
    def detect_vehicle(self,frame:np.ndarray)->List[Vehicle]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        canny = cv2.Canny(gray, 50, 150, apertureSize=3)
        contours,_ = cv2.findContours(canny, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        detected_vehicles = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 1000<area<10000:
                x,y,w,h = cv2.boundingRect(contour)
            else:
                continue
            if area> self.truck_size_threshold:
                vehicle_type = VehicleType.TRUCK
            else:
                vehicle_type = VehicleType.CAR
            center = (x+w//2,y+h//2)
            distance = self.estimate_distance(area,vehicle_type)
            speed = self.estimate_speed()
            vehicle = Vehicle( vehicle_id= self.vehicle_counter,
                                vehicle_type= vehicle_type,
                                trajectory= deque(maxlen=30),
                                center= center,
                                bbox=(x, y, w, h),
                                speed= speed,
                                distance= distance,
                                is_high_beam_on = False,
                                lane=self.estimate_lane(center[0],frame.shape[1]))
            vehicle.trajectory.append(center)
            detected_vehicles.append(vehicle)
            self.vehicle_counter += 1
        return detected_vehicles
    def estimate_distance(self,area,vehicle_type:VehicleType)->float:
        if vehicle_type == VehicleType.CAR:
            distance = 150/(math.sqrt(area)/100 + 1)
        else:
            distance = 200/(math.sqrt(area)/100 + 1)
        return max(5,min(distance,200))
    def estimate_speed(self)->float:
        return np.random.uniform(30,170)
    def estimate_lane(self,x_center,frame_width)->str:
        lane_width = frame_width/3
        if x_center<lane_width:
            lane = "left"
        elif x_center<2*lane_width:
            lane = "center"
        else:
            lane = "right"
        return lane

class DetectHighBeam:
    def __init__(self):
        self.glare_threshold = 200
        self.glare_area_threshold = 0.5
    def detect_high_beam(self,frame:np.ndarray)->Tuple[bool,float]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h,w = gray.shape
        upper_half = gray[:h//2,:]
        bright_in_upper = np.sum(upper_half>self.glare_threshold)
        upper_bright_ratio = bright_in_upper/(upper_half.shape[0]*upper_half.shape[1])
        is_glare = upper_bright_ratio > 0.2
        glare_percentage = min(upper_bright_ratio*10,1.0)
        return is_glare,glare_percentage
    def detect_oncoming_vehicle_headlight(self, frame: np.ndarray) -> List[Tuple[int, int]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        upper_half = gray[:h // 2, :]
        _,thresh = cv2.threshold(upper_half, 200, 255, cv2.THRESH_BINARY)
        contours,_ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        headlights = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 50 < area < 500:
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    headlights.append((cx, cy))
        return headlights

class LaneChangeAssist:
    def __init__(self):
        self.min_safe_distance = 180
        self.min_speed_difference = 25
        self.safe_lane_clearance = 60
    def analyze_lane_change(self,frame:np.ndarray,ego_vehicle,ego_speed,vehicles:List[Vehicle])->Optional[Alert]:
        vehicles_ahead = [v for v in vehicles if v.distance > 0 and v.distance < 200 and v.lane == ego_vehicle.lane]  # ✅ same lane only
        if not vehicles_ahead:
            return None
        front_vehicle = min(vehicles_ahead, key=lambda v: v.distance)
        print("Front vehicle center:", front_vehicle.center)
        print("Ego center:", ego_vehicle.center)
        print("Distance:", front_vehicle.distance)
        print("Min safe distance:", self.min_safe_distance)
        if front_vehicle.vehicle_type in (VehicleType.TRUCK, VehicleType.BUS,VehicleType.CAR) and front_vehicle.distance<self.min_safe_distance and ego_speed > 40:
            left_lane_safe = self.is_lane_safe("left",ego_vehicle,vehicles)
            right_lane_safe = self.is_lane_safe("right",ego_vehicle,vehicles)
            if left_lane_safe or right_lane_safe:
                if right_lane_safe:
                    safe_lane = "right"
                elif left_lane_safe:
                    safe_lane = "left"
                return Alert(
                    level=AlertLevel.WARNING,
                    title="Lane Change Suggested",
                    message=f"Large vehicle ahead ({front_vehicle.vehicle_type.value}) at {front_vehicle.distance:.1f}m. Moving {ego_speed:.0f} km/h.",
                    recommendation=f"Safe to change to {safe_lane} lane. Check mirrors and signal before changing.",
                    timestamp=datetime.now(),
                    duration=8
                )
            else:
                return Alert(
                    level=AlertLevel.WARNING,
                    title="Reduce Speed",
                    message=f"Large vehicle ahead. Lanes busy. Maintain distance.",
                    recommendation="Reduce speed to safe following distance (keep 3+ seconds behind truck).",
                    timestamp=datetime.now(),
                    duration=5
                )
        print("Front distance:", front_vehicle.distance)
        return None
    def is_lane_safe(self,target_lane:str,ego_vehicle,vehicles:List[Vehicle])->bool:
        if target_lane == ego_vehicle.lane:
            return False
        vehicles_in_lane = [v for v in vehicles if v.lane==target_lane]
        for vehicle in vehicles_in_lane:
            if abs(vehicle.center[1]- ego_vehicle.center[1])<self.safe_lane_clearance*10:
                return False
        return True

class TrajectoryPredictor:
    def __init__(self):
        self.prediction_frames = 30
    def predict_collision(self,ego_vehicle,other_vehicle:List[Vehicle],ego_speed)->Optional[Alert]:
        for vehicle in other_vehicle:
            ego_vehicle_future = [ego_vehicle.center[0],ego_vehicle.center[1] + ego_speed * self.prediction_frames]
            other_vehicle_future = vehicle.predict_position(self.prediction_frames)
            distance = math.sqrt((ego_vehicle_future[0] - other_vehicle_future[0]) ** 2 + (ego_vehicle_future[1] - other_vehicle_future[1]) ** 2)
            if distance < 50:  # pixels = potential collision
                return Alert(
                    level=AlertLevel.CRITICAL,
                    title="Collision Risk Detected",
                    message=f"{vehicle.vehicle_type.value.capitalize()} in path. {distance:.0f}px away.",
                    recommendation="SLOW DOWN immediately! Apply brakes cautiously.",
                    timestamp=datetime.now(),
                    duration=10
                )
        return None

class ADAS:
    def __init__(self):
        self.high_beam_detector = DetectHighBeam()
        self.vehicle_detector = DetectVehicle()
        self.lane_change_assistant = LaneChangeAssist()
        self.trajectory_predictor = TrajectoryPredictor()
        self.ego_speed = 60  # km/h (would come from CAN bus in real car)
        self.ego_vehicle = None
        self.alerts: deque = deque(maxlen=10)
        self.frame_count = 0
    def process_frame(self,frame:np.ndarray)->dict:
        glare_detected,glare_intensity = self.high_beam_detector.detect_high_beam(frame)
        if glare_detected and glare_intensity>0.5:
            alert = Alert(
                level=AlertLevel.WARNING,
                title="High Beam Glare Detected",
                message=f"Oncoming vehicle has high beam on (intensity: {glare_intensity:.0%}).",
                recommendation="Shield eyes, reduce speed slightly, and prepare for defensive driving.",
                timestamp=datetime.now(),
                duration=6
            )
            self.alerts.append(alert)
        vehicles = self.vehicle_detector.detect_vehicle(frame)
        h, w = frame.shape[:2]
        self.ego_vehicle = Vehicle(
            vehicle_id=-1,
            vehicle_type=VehicleType.CAR,
            center=(w // 2, h - 40),
            bbox=(w//2-20, h-80, 40, 80),
            distance=0,
            speed=self.ego_speed,
            trajectory=deque(maxlen=30),
            is_high_beam_on=False,
            lane="center"
        )
        self.ego_vehicle.trajectory.append(self.ego_vehicle.center)
        self.frame_count += 1
        return {
            "frame": frame,
            "vehicles": vehicles,
            "ego_vehicle": self.ego_vehicle,
            "alerts": list(self.alerts),
            "glare_detected": glare_detected,
            "glare_intensity": glare_intensity,
            "oncoming_headlights": [],
            "frame_count": self.frame_count
        }
    def visualize(self, result: dict) -> np.ndarray:
        """Create annotated frame with detections and alerts"""
        frame = result["frame"].copy()
        h, w = frame.shape[:2]

        # Draw road lanes
        lane_width = w // 3
        cv2.line(frame, (lane_width, 0), (lane_width, h), (255, 255, 0), 2)
        cv2.line(frame, (2 * lane_width, 0), (2 * lane_width, h), (255, 255, 0), 2)

        # Draw detected vehicles
        for vehicle in result["vehicles"]:
            x, y, vw, vh = vehicle.bbox
            color = (0, 255, 0) if vehicle.vehicle_type == VehicleType.CAR else (0, 165, 255)
            cv2.rectangle(frame, (x, y), (x + vw, y + vh), color, 2)
            cv2.putText(frame, f"{vehicle.vehicle_type.value} {vehicle.distance:.1f}m",
                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Draw trajectory
            if len(vehicle.trajectory) > 1:
                points = np.array(vehicle.get_trajectory_points(), dtype=np.int32)
                cv2.polylines(frame, [points], False, color, 1)

            # Draw predicted position
            pred = vehicle.predict_position()
            cv2.circle(frame, tuple(map(int, pred)), 5, (255, 0, 0), 2)

        # Draw ego vehicle
        ego = result["ego_vehicle"]
        x, y, vw, vh = ego.bbox
        cv2.rectangle(frame, (x, y), (x + vw, y + vh), (0, 0, 255), 3)
        cv2.putText(frame, "EGO", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Draw oncoming headlights
        if result["oncoming_headlights"]:
            for hx, hy in result["oncoming_headlights"]:
                cv2.circle(frame, (hx, hy), 10, (0, 255, 255), 2)

        # Draw glare indicator
        if result["glare_detected"]:
            intensity = result["glare_intensity"]
            color = (0, 0, int(255 * intensity))
            cv2.rectangle(frame, (10, 10), (200, 50), color, -1)
            cv2.putText(frame, f"HIGH BEAM GLARE {intensity:.0%}",
                        (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Draw alerts
        alert_y = 70
        for alert in result["alerts"]:
            color_map = {
                AlertLevel.INFO: (0, 255, 0),
                AlertLevel.WARNING: (0, 165, 255),
                AlertLevel.CRITICAL: (0, 0, 255)
            }
            color = color_map[alert.level]

            cv2.rectangle(frame, (10, alert_y), (w - 10, alert_y + 60), color, 2)
            cv2.putText(frame, f"{alert.title}",
                        (20, alert_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            cv2.putText(frame, alert.message,
                        (20, alert_y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            alert_y += 65

        # Draw HUD info
        cv2.putText(frame, f"Speed: {self.ego_speed:.0f} km/h | Frame: {result['frame_count']}",
                    (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame
    def get_lane_decision(self, ego_vehicle_dict, vehicles_dict, ego_speed):

        ego_lane = str(ego_vehicle_dict["lane"])
        ego_center_list = list(ego_vehicle_dict["center"])
        ego_center_x = float(ego_center_list[0])
        ego_center_y = float(ego_center_list[1])

        print(f"[DEBUG] ego_center=({ego_center_x},{ego_center_y}), lane={ego_lane}, speed={float(ego_speed)}")

        vehicles = []
        for i, v in enumerate(vehicles_dict):
            lane = str(v["lane"])
            center_list = list(v["center"])
            center_x = float(center_list[0])
            center_y = float(center_list[1])
            distance = float(v["distance"])

            print(f"[DEBUG] Vehicle {i}: lane={lane}, center=({center_x},{center_y}), distance={distance}")

            vehicle = Vehicle(
                vehicle_id=i,
                vehicle_type=VehicleType.TRUCK if str(v["type"]) == "truck" else (VehicleType.BUS if str(v["type"]) == "bus" else VehicleType.CAR),
                trajectory=deque(maxlen=30),
                center=(center_x, center_y),
                bbox=(center_x-20, center_y-40, 40, 80),
                speed=float(v["speed"]) if "speed" in v.keys() else 50,
                distance=distance,
                is_high_beam_on=False,
                lane=lane
            )
            vehicles.append(vehicle)

        ego_vehicle = Vehicle(
            vehicle_id=-1,
            vehicle_type=VehicleType.CAR,
            trajectory=deque(maxlen=30),
            center=(ego_center_x, ego_center_y),
            bbox=(ego_center_x-20, ego_center_y-40, 40, 80),
            speed=float(ego_speed),
            distance=0,
            is_high_beam_on=False,
            lane=ego_lane
        )

        alert = self.lane_change_assistant.analyze_lane_change(
            None, ego_vehicle, float(ego_speed), vehicles
        )

        print(f"[DEBUG] Alert={alert}")

        if alert is None:
            return "none"
        if "left" in alert.recommendation.lower():
            return "left"
        if "right" in alert.recommendation.lower():
            return "right"
        if "reduce speed" in alert.title.lower():
            return "slow" 
        return "none"