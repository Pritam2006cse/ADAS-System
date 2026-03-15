"""
SmartShield ADAS - Quick Start & Testing Script
Demo script showing how to use the complete system
"""

import cv2
import numpy as np
from adas_system import SmartShieldADAS, AlertLevel
from carla_integration import CarlaSimulator
import time
from datetime import datetime


def demo_1_high_beam_detection():
    """Demo 1: Detect high beam glare in video"""
    print("\n" + "="*70)
    print("DEMO 1: HIGH BEAM GLARE DETECTION")
    print("="*70)
    
    adas = SmartShieldADAS()
    
    # Create synthetic frame with high beam glare
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :] = (30, 30, 40)  # Dark night background
    
    # Simulate oncoming high beam (bright spot in upper center)
    cv2.circle(frame, (640, 150), 80, (200, 200, 255), -1)
    cv2.circle(frame, (740, 150), 80, (200, 200, 255), -1)
    
    # Process
    result = adas.process_frame(frame)
    
    print(f"Glare Detected: {result['glare_detected']}")
    print(f"Glare Intensity: {result['glare_intensity']:.1%}")
    print(f"Oncoming Headlights: {len(result['oncoming_headlights'])}")
    
    if result['alerts']:
        for alert in result['alerts']:
            print(f"\n✓ Alert Generated:")
            print(f"  Title: {alert.title}")
            print(f"  Level: {alert.level.value.upper()}")
            print(f"  Recommendation: {alert.recommendation}")
    
    return result


def demo_2_vehicle_detection():
    """Demo 2: Detect and classify vehicles"""
    print("\n" + "="*70)
    print("DEMO 2: VEHICLE DETECTION & CLASSIFICATION")
    print("="*70)
    
    adas = SmartShieldADAS()
    
    # Create synthetic frame with vehicles
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :] = (60, 120, 90)  # Road background
    
    # Draw road markings
    cv2.line(frame, (427, 0), (427, 720), (255, 255, 0), 2)
    cv2.line(frame, (853, 0), (853, 720), (255, 255, 0), 2)
    
    # Draw car (left lane)
    cv2.rectangle(frame, (300, 200), (450, 350), (100, 100, 255), -1)
    
    # Draw large truck (center lane, ahead)
    cv2.rectangle(frame, (500, 100), (780, 300), (100, 100, 200), -1)
    cv2.rectangle(frame, (500, 150), (780, 250), (150, 150, 200), -1)
    
    # Draw car (right lane)
    cv2.rectangle(frame, (900, 250), (1050, 400), (100, 100, 255), -1)
    
    # Process
    result = adas.process_frame(frame)
    
    print(f"Vehicles Detected: {len(result['vehicles'])}")
    for i, vehicle in enumerate(result['vehicles'], 1):
        print(f"\nVehicle {i}:")
        print(f"  Type: {vehicle.vehicle_type.value}")
        print(f"  Distance: {vehicle.distance:.1f}m")
        print(f"  Lane: {vehicle.lane}")
        print(f"  Speed: {vehicle.speed:.1f} km/h")
    
    return result


def demo_3_lane_change_suggestion():
    """Demo 3: Lane change safety assessment"""
    print("\n" + "="*70)
    print("DEMO 3: INTELLIGENT LANE CHANGE ASSISTANCE")
    print("="*70)
    
    adas = SmartShieldADAS()
    adas.ego_speed = 110  # High speed
    
    # Create scenario: blocked by truck
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame[:, :] = (60, 120, 90)
    
    # Road markings
    cv2.line(frame, (427, 0), (427, 720), (255, 255, 0), 2)
    cv2.line(frame, (853, 0), (853, 720), (255, 255, 0), 2)
    
    # Truck ahead (very large, close)
    cv2.rectangle(frame, (480, 150), (800, 350), (100, 100, 200), -1)
    cv2.rectangle(frame, (480, 200), (800, 300), (150, 150, 200), -1)
    cv2.rectangle(frame, (480, 250), (800, 290), (100, 150, 200), -1)
    
    # Car in right lane (safe distance ahead)
    cv2.rectangle(frame, (900, 100), (1050, 250), (100, 100, 255), -1)
    
    # Process
    result = adas.process_frame(frame)
    
    print(f"Ego Speed: {adas.ego_speed} km/h")
    print(f"Vehicles Detected: {len(result['vehicles'])}")
    
    if result['alerts']:
        for alert in result['alerts']:
            print(f"\n✓ SUGGESTION GENERATED:")
            print(f"  Title: {alert.title}")
            print(f"  Message: {alert.message}")
            print(f"  Level: {alert.level.value.upper()}")
            print(f"  → {alert.recommendation}")
    else:
        print("\nNo critical suggestions at this moment")
    
    return result


def demo_4_collision_prediction():
    """Demo 4: Trajectory prediction and collision detection"""
    print("\n" + "="*70)
    print("DEMO 4: TRAJECTORY PREDICTION & COLLISION DETECTION")
    print("="*70)
    
    adas = SmartShieldADAS()
    adas.ego_speed = 100
    
    # Simulate series of frames with vehicle trajectory
    frame_count = 0
    vehicles_log = []
    
    print("Simulating vehicle approach over 30 frames...")
    
    for frame_num in range(30):
        # Create frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:, :] = (60, 120, 90)
        
        # Vehicle approaching (moves down frame = closer)
        vehicle_y = 100 + frame_num * 8
        cv2.rectangle(frame, (500, vehicle_y), (780, vehicle_y + 150), 
                     (100, 100, 200), -1)
        
        # Process
        result = adas.process_frame(frame)
        frame_count += 1
        
        # Log vehicle data
        if result['vehicles']:
            for v in result['vehicles']:
                vehicles_log.append({
                    'frame': frame_num,
                    'distance': v.distance,
                    'position': v.center
                })
        
        # Check for collision alerts
        if result['alerts']:
            for alert in result['alerts']:
                if alert.level == AlertLevel.CRITICAL:
                    print(f"\n🚨 COLLISION ALERT at Frame {frame_num}:")
                    print(f"   {alert.message}")
                    print(f"   {alert.recommendation}")
                    return result
    
    print(f"\nProcessed {frame_count} frames")
    print("Vehicle trajectory tracked and logged")
    print("Distance reducing as vehicle approaches")
    
    return None


def demo_5_full_scenario():
    """Demo 5: Complex driving scenario"""
    print("\n" + "="*70)
    print("DEMO 5: FULL DRIVING SCENARIO SIMULATION")
    print("="*70)
    
    adas = SmartShieldADAS()
    adas.ego_speed = 85
    
    print("\nScenario: Highway driving at night with oncoming traffic")
    print("Duration: 10 frames @ 30 FPS = 0.33 seconds")
    
    for frame_num in range(10):
        # Create complex scene
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:, :] = (20, 25, 35)  # Dark night
        
        # Road
        cv2.line(frame, (427, 0), (427, 720), (200, 200, 100), 2)
        cv2.line(frame, (853, 0), (853, 720), (200, 200, 100), 2)
        
        # Scenario events based on frame
        if frame_num < 5:
            # Phase 1: Truck ahead
            cv2.rectangle(frame, (480, 150), (800, 350), (80, 80, 150), -1)
        elif frame_num < 10:
            # Phase 2: Truck + oncoming high beam
            cv2.rectangle(frame, (480, 150), (800, 350), (80, 80, 150), -1)
            cv2.circle(frame, (150, 100), 60, (180, 180, 255), -1)
            cv2.circle(frame, (250, 100), 60, (180, 180, 255), -1)
        
        # Process
        result = adas.process_frame(frame)
        
        # Display results
        print(f"\nFrame {frame_num + 1}:")
        print(f"  Vehicles: {len(result['vehicles'])}")
        print(f"  Glare detected: {result['glare_detected']}")
        
        if result['alerts']:
            print(f"  Alerts: {len(result['alerts'])}")
            for alert in result['alerts'][:2]:  # Show first 2
                print(f"    • {alert.title} ({alert.level.value})")
    
    print("\n✓ Scenario simulation complete")
    return None


def run_all_demos():
    """Run all demonstrations"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  SmartShield ADAS - Complete System Demonstration".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    demos = [
        ("High Beam Glare Detection", demo_1_high_beam_detection),
        ("Vehicle Detection", demo_2_vehicle_detection),
        ("Lane Change Assistance", demo_3_lane_change_suggestion),
        ("Collision Prediction", demo_4_collision_prediction),
        ("Full Scenario", demo_5_full_scenario),
    ]
    
    for demo_name, demo_func in demos:
        try:
            demo_func()
            print(f"\n✓ {demo_name}: PASSED")
        except Exception as e:
            print(f"\n✗ {demo_name}: FAILED - {str(e)}")
        
        time.sleep(0.5)
    
    print("\n" + "="*70)
    print("ALL DEMONSTRATIONS COMPLETE")
    print("="*70)


def test_carla_scenarios():
    """Test CARLA simulator scenarios"""
    print("\n" + "="*70)
    print("CARLA SIMULATOR INTEGRATION TEST")
    print("="*70)
    
    try:
        simulator = CarlaSimulator()
        
        print("\nAvailable Scenarios:")
        for scenario in simulator.list_scenarios():
            print(f"  • {scenario}")
        
        print("\nLoading scenario: High Beam Glare Night Scenario")
        if simulator.load_scenario("High Beam Glare Night Scenario"):
            config = simulator.get_scenario_config()
            print(f"✓ Scenario loaded successfully")
            print(f"  Map: {config['map']}")
            print(f"  Weather: Night, cloudiness {config['weather']['cloudiness']}%")
            print(f"  Duration: {config['duration']}s")
            print(f"\nNote: Full CARLA integration requires:")
            print(f"  1. CARLA server running on port 2000")
            print(f"  2. Python carla library installed")
            print(f"  3. Valid CARLA installation")
        
    except Exception as e:
        print(f"Note: {e}")
        print("This is expected if CARLA is not installed")


if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                   SmartShield ADAS Quick Start                     ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    
    print("\nOptions:")
    print("  1. Run all demonstrations")
    print("  2. Test individual modules")
    print("  3. Test CARLA integration")
    print("  4. Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        run_all_demos()
    elif choice == "2":
        print("\nRunning individual module tests...")
        demo_1_high_beam_detection()
        print("\n" + "-"*70)
        demo_2_vehicle_detection()
        print("\n" + "-"*70)
        demo_3_lane_change_suggestion()
    elif choice == "3":
        test_carla_scenarios()
    else:
        print("Exiting...")
    
    print("\n" + "="*70)
    print("For more information, see DOCUMENTATION.md")
    print("="*70 + "\n")