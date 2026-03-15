clear
clc
close all

%% Set path
projectPath = "C:\Users\KIIT\OneDrive\Desktop\ADASity\Adas";
if count(py.sys.path, projectPath) == 0
    insert(py.sys.path, int32(0), projectPath);
end

if py.bool(py.hasattr(py.sys.modules, 'adas_system'))
    py.importlib.reload(py.importlib.import_module('adas_system'));
end

adas = py.adas_system.ADAS();
disp("Python ADAS module loaded successfully")

%% Road parameters
lane_width       = 200;
road_width       = 600;
road_height      = 800;
lane_centers     = [100 300 500];
lane_names       = ["left", "center", "right"];
pixels_per_meter = 3.0;
fps              = 20;
sim_speed_mult   = 2.5;

%% Vehicle type definitions
vehicle_types  = ["car", "truck", "bus"];
vehicle_colors = {[0 0.8 0], [0.8 0 0], [0.8 0.4 0]};
vehicle_labels = ["CAR", "TRUCK", "BUS"];

function [vtype, vcolor, vlabel] = random_vehicle(vtypes, vcolors, vlabels)
    idx    = randi(3);
    vtype  = vtypes(idx);
    vcolor = vcolors{idx};
    vlabel = vlabels(idx);
end

function sz = get_vehicle_size(vtype)
    if vtype == "truck" || vtype == "bus"
        sz = [60 100];
    else
        sz = [40 80];
    end
end

%% Ego initial state
ego_lane     = 2;
ego_visual_y = 200;
ego_speed    = 60 + randi(40);

%% Smooth lane change
ego_x_current        = lane_centers(ego_lane);
ego_x_target         = lane_centers(ego_lane);
lane_change_smooth_speed = 8;

%% 3 traffic vehicles
num_vehicles = 5;
v_types  = cell(num_vehicles, 1);
v_colors = cell(num_vehicles, 1);
v_labels = cell(num_vehicles, 1);
v_lanes  = zeros(num_vehicles, 1);
v_screen_y = zeros(num_vehicles, 1);
v_speeds   = zeros(num_vehicles, 1);

%% Initialize vehicles
for i = 1:num_vehicles
    [v_types{i}, v_colors{i}, v_labels{i}] = random_vehicle( ...
        vehicle_types, vehicle_colors, vehicle_labels);

    lane_ok  = false;
    attempts = 0;
    while ~lane_ok && attempts < 20
        candidate_lane = randi(3);
        too_close = false;
        for j = 1:i-1
            if v_lanes(j) == candidate_lane && ...
               abs(v_screen_y(j) - (ego_visual_y + 200 + (i-1)*150)) < 150
                too_close = true;
                break
            end
        end
        if ~too_close
            lane_ok    = true;
            v_lanes(i) = candidate_lane;
        end
        attempts = attempts + 1;
    end
    if ~lane_ok
        v_lanes(i) = mod(i-1, 3) + 1;
    end

    v_screen_y(i) = ego_visual_y + 400 + randi(200);
    v_speeds(i)   = max(30, ego_speed - 30 + randi(60));
end

%% Force v1 as truck in center lane
v_types{1}    = "truck";
v_colors{1}   = vehicle_colors{2};
v_labels{1}   = "TRUCK";
v_lanes(1)    = 2;
v_screen_y(1) = ego_visual_y + 250;

%% State
lane_change_cooldown = 0;
decision             = "none";
display_decision     = "none";
scenario_count       = 0;
frame_count          = 0;
road_offset          = 0;
is_animating         = false;

figure('Color','black','Position',[100 100 700 900])

while true

    frame_count = frame_count + 1;

    clf
    axis([0 road_width 0 road_height])
    axis manual
    set(gca,'YDir','normal')
    hold on
    set(gca,'Color',[0.15 0.15 0.15])

    %% Road scroll
    pix_ego = ego_speed * 0.278 / fps * pixels_per_meter * sim_speed_mult;
    road_offset = mod(road_offset + pix_ego, 60);

    %% Road surface
    rectangle('Position',[0 0 road_width road_height], ...
        'FaceColor',[0.22 0.22 0.22],'EdgeColor','white','LineWidth',3)

    %% Scrolling lane dashes
    for yy = -60:60:road_height+60
        ypos = yy + road_offset;
        if ypos > 0 && ypos < road_height
            rectangle('Position',[lane_width-2 ypos 4 35], ...
                'FaceColor','yellow','EdgeColor','none')
            rectangle('Position',[2*lane_width-2 ypos 4 35], ...
                'FaceColor','yellow','EdgeColor','none')
        end
    end

    %% Scrolling edge markers
    for yy = -30:30:road_height+30
        ypos = yy + road_offset;
        if ypos > 0 && ypos < road_height
            rectangle('Position',[5 ypos 8 20], ...
                'FaceColor',[0.5 0.5 0.5],'EdgeColor','none')
            rectangle('Position',[road_width-13 ypos 8 20], ...
                'FaceColor',[0.5 0.5 0.5],'EdgeColor','none')
        end
    end

    %% Lane labels
    text(lane_centers(1), road_height-20, "LEFT", ...
        'Color','yellow','FontSize',10,'HorizontalAlignment','center')
    text(lane_centers(2), road_height-20, "CENTER", ...
        'Color','yellow','FontSize',10,'HorizontalAlignment','center')
    text(lane_centers(3), road_height-20, "RIGHT", ...
        'Color','yellow','FontSize',10,'HorizontalAlignment','center')

    %% Draw 3 traffic vehicles
    for i = 1:num_vehicles
        sz = get_vehicle_size(v_types{i});
        vw = sz(1); vh = sz(2);
        vx = lane_centers(v_lanes(i));
        vy = v_screen_y(i);

        if vy >= -vh && vy <= road_height + vh
            rectangle('Position',[vx-vw/2 vy-vh/2 vw vh], ...
                'FaceColor',v_colors{i},'EdgeColor','white','LineWidth',2)
            text(vx, vy, v_labels{i}, ...
                'Color','white','FontSize',8,'HorizontalAlignment','center')
            text(vx, vy-vh/2-12, sprintf('%.0f km/h', v_speeds(i)), ...
                'Color','white','FontSize',7,'HorizontalAlignment','center')
        end
    end

    %% Smooth ego X slide
    if ego_x_current < ego_x_target
        ego_x_current = min(ego_x_current + lane_change_smooth_speed, ego_x_target);
    elseif ego_x_current > ego_x_target
        ego_x_current = max(ego_x_current - lane_change_smooth_speed, ego_x_target);
    end

    %% Draw ego
    rectangle('Position',[ego_x_current-20 ego_visual_y-40 40 80], ...
        'FaceColor','blue','EdgeColor','white','LineWidth',2)
    text(ego_x_current, ego_visual_y, "EGO", ...
        'Color','white','FontSize',8,'HorizontalAlignment','center')
    text(ego_x_current, ego_visual_y-55, sprintf('%.0f km/h', ego_speed), ...
        'Color','cyan','FontSize',7,'HorizontalAlignment','center')

    %% Speed lines beside ego
    num_lines = floor(ego_speed / 12);
    for i = 1:num_lines
        line_y   = ego_visual_y - 35 + randi(70);
        line_len = 8 + floor(ego_speed / 15);
        plot([ego_x_current-28 ego_x_current-28],[line_y line_y-line_len], ...
            'Color',[0.8 0.8 0.8],'LineWidth',0.8)
        plot([ego_x_current+28 ego_x_current+28],[line_y line_y-line_len], ...
            'Color',[0.8 0.8 0.8],'LineWidth',0.8)
    end

    %% Scenario info
    text(20, 655, "Scenario #" + scenario_count, 'Color','cyan','FontSize',9)

    %% ✅ Derive ego lane from actual X position
    distances_to_lanes = abs(lane_centers - ego_x_current);
    [~, actual_lane_idx] = min(distances_to_lanes);
    ego_lane     = actual_lane_idx;
    ego_lane_str = lane_names(actual_lane_idx);

    %% ✅ Do not call Python while ego is sliding
    is_animating = abs(ego_x_current - ego_x_target) > 5;

    if lane_change_cooldown > 0
        lane_change_cooldown = lane_change_cooldown - 1;
        decision = "cooldown";

    elseif is_animating
        decision = "animating";

    else
        %% Build Python vehicle list
        vehicles_py = py.list();
        for i = 1:num_vehicles
            v_world_dist = (v_screen_y(i) - ego_visual_y) / pixels_per_meter;
            vx_i = lane_centers(v_lanes(i));

            v_dict = py.dict(pyargs( ...
                'lane',     lane_names(v_lanes(i)), ...
                'type',     v_types{i}, ...
                'speed',    v_speeds(i), ...        % ✅ actual vehicle speed
                'center',   py.tuple(int32([vx_i int32(v_screen_y(i))])), ...
                'distance', v_world_dist ...
            ));
            vehicles_py.append(v_dict);
        end

        ego_vehicle = py.dict(pyargs( ...
            'lane',   ego_lane_str, ...             % ✅ from actual X position
            'center', py.tuple(int32([int32(ego_x_current) ego_visual_y])) ...
        ));

        try
            decision = string(char(adas.get_lane_decision( ...
                ego_vehicle, vehicles_py, ego_speed)));
        catch ME
            disp("ERROR: " + ME.message)
            decision = "none";
        end

        %% ✅ Apply decision
        if decision == "left" && ego_lane > 1
            ego_lane     = ego_lane - 1;
            ego_x_target = lane_centers(ego_lane);
            lane_change_cooldown = 50;

        elseif decision == "right" && ego_lane < 3
            ego_lane     = ego_lane + 1;
            ego_x_target = lane_centers(ego_lane);
            lane_change_cooldown = 50;

        elseif decision == "slow"
            %% ✅ Both lanes blocked — reduce ego speed
            ego_speed = max(30, ego_speed - 5);
            disp("⚠️ ADAS: Reducing speed — lanes busy, ego now " + ego_speed + " km/h")
        end
    end

    %% ✅ Emergency braking — if any vehicle in same lane is very close
    for i = 1:num_vehicles
        v_world_dist_check = (v_screen_y(i) - ego_visual_y) / pixels_per_meter;
        if v_lanes(i) == ego_lane && ...
           v_world_dist_check > 0 && v_world_dist_check < 60
            ego_speed = max(20, ego_speed - 8);
            disp("🚨 Emergency brake — vehicle " + i + " at " + ...
                 sprintf('%.1f', v_world_dist_check) + "m")
        end
    end

    display_decision = decision;

    %% Move vehicles by relative speed
    for i = 1:num_vehicles
        pix_vi = v_speeds(i) * 0.278 / fps * pixels_per_meter * sim_speed_mult;
        v_screen_y(i) = v_screen_y(i) + (pix_vi - pix_ego);
    end

    %% Vary speeds
    if mod(frame_count, 60) == 0
        ego_speed = max(40, min(120, ego_speed + randi([-8 8])));
    end
    if mod(frame_count, 40) == 0
        for i = 1:num_vehicles
            v_speeds(i) = max(20, min(130, v_speeds(i) + randi([-5 5])));
        end
    end

    %% Reset vehicles that go off screen
    for i = 1:num_vehicles
        if v_screen_y(i) < ego_visual_y - 250 || ...
           v_screen_y(i) > road_height + 200

            if i == 1
                scenario_count = scenario_count + 1;
                disp("=== New Scenario #" + scenario_count + " ===")

                %% ✅ Keep ego in current lane — do not reset
                lane_change_cooldown = 60;
                decision             = "none";
                display_decision     = "none";
                ego_speed            = 50 + randi(50);

                %% Spawn v1 as truck/bus in center most of the time
                if rand < 0.7
                    idx         = randi([2 3]);
                    v_types{1}  = vehicle_types(idx);
                    v_colors{1} = vehicle_colors{idx};
                    v_labels{1} = vehicle_labels(idx);
                    v_lanes(1)  = 2;
                else
                    [v_types{1}, v_colors{1}, v_labels{1}] = ...
                        random_vehicle(vehicle_types, vehicle_colors, vehicle_labels);
                    v_lanes(1) = randi(3);
                end

                v_screen_y(1) = ego_visual_y + 300 + randi(100);
                v_speeds(1)   = max(20, ego_speed - 30 + randi(60));

                disp("Ego stays in lane: " + lane_names(ego_lane) + ...
                     "  speed=" + ego_speed)
                disp("V1: " + v_types{1} + "  Lane=" + lane_names(v_lanes(1)))
                for j = 2:num_vehicles
                    [v_types{j}, v_colors{j}, v_labels{j}] = ...
                        random_vehicle(vehicle_types, vehicle_colors, vehicle_labels);
                    candidate = mod(j-1, 3) + 1;
                    if candidate == ego_lane
                        candidate = mod(j, 3) + 1;
                    end
                    v_lanes(j)    = candidate;
                    v_screen_y(j) = ego_visual_y + 400 + (j-2)*150 + randi(80);
                    v_speeds(j)   = max(20, ego_speed - 30 + randi(60));
                end
            else
                %% Respawn other vehicles from top
                [v_types{i}, v_colors{i}, v_labels{i}] = ...
                    random_vehicle(vehicle_types, vehicle_colors, vehicle_labels);

                %% ✅ Don't spawn in ego's current lane too close
                best_lane = randi(3);
                for attempt = 1:15
                    candidate = randi(3);
                    crowded   = false;

                    %% Avoid ego lane for respawns
                    if candidate == ego_lane
                        continue
                    end

                    for j = 1:num_vehicles
                        if j ~= i && v_lanes(j) == candidate && ...
                           abs(v_screen_y(j) - (road_height + 100)) < 180
                            crowded = true;
                            break
                        end
                    end
                    if ~crowded
                        best_lane = candidate;
                        break
                    end
                end
                v_lanes(i)    = best_lane;
                v_screen_y(i) = ego_visual_y + 80 + randi(200);
                v_speeds(i)   = max(20, ego_speed - 30 + randi(60));
            end
        end
    end

    %% HUD color
    if display_decision == "left" || display_decision == "right"
        hudColor = [0.8 0.4 0];
    elseif display_decision == "slow"
        hudColor = [0.6 0.0 0.0];       % ✅ dark red for braking
    elseif display_decision == "cooldown"
        hudColor = [0.2 0.2 0.6];
    elseif display_decision == "animating"
        hudColor = [0.1 0.3 0.1];
    else
        hudColor = [0.1 0.1 0.1];
    end

    rectangle('Position',[10 740 340 50], ...
        'FaceColor',hudColor,'EdgeColor','white','LineWidth',1)
    text(20, 770, "ADAS: " + upper(display_decision), ...
        'Color','white','FontSize',14,'FontWeight','bold')
    text(360, 770, "Ego: " + sprintf('%.0f',ego_speed) + " km/h", ...
        'Color','cyan','FontSize',12,'FontWeight','bold')

    %% Vehicle distances
    info_str = "";
    for i = 1:num_vehicles
        vd = (v_screen_y(i) - ego_visual_y) / pixels_per_meter;
        info_str = info_str + "V" + i + ":" + ...
            sprintf('%.0f',vd) + "m " + sprintf('%.0f',v_speeds(i)) + "kmh  ";
    end
    text(10, 725, info_str, 'Color','white','FontSize',9)

    text(20, 700, "Ego lane: " + upper(lane_names(ego_lane)) + ...
        "  |  Cooldown: " + lane_change_cooldown, ...
        'Color','yellow','FontSize',10)

    if lane_change_cooldown > 0 || is_animating
        text(20, 675, "Lane change in progress...", ...
            'Color',[1 0.5 0],'FontSize',10)
    end

    drawnow
    pause(0.03)

end