%% RAPID-0 Communication Window Analysis
%  Ground Station: UCLA (34.069°N, 118.443°W)
%  Satellite: RAPID-0 @ 450 km, 34.75° inclination
%  Mission: 2026-Jun-01 to 2026-Sep-02 (93 days)
% -------------------------------------------------------

%% 1. Mission & Orbit Parameters
MISSION_START            = datetime(2026, 6, 1, 8, 0, 0, 0);
MISSION_END              = MISSION_START + days(93);
ORBIT_RADIUS             = (6378 + 450) * 1000;   % metres
ORBITAL_INCLINATION_DEG  = 34.75;                  % degrees

MIN_ELEVATION_DEG = 5;   % minimum usable elevation above horizon (degrees)

%% 2. Build Satellite Scenario (60-second time step)
disp("Building satellite scenario...");
simulation = satelliteScenario(MISSION_START, MISSION_END, 60);

%% 3. Add RAPID-0 Satellite
rapid_0 = satellite( ...
    simulation, ...
    ORBIT_RADIUS, ...
    0, ...                      % eccentricity (circular orbit)
    ORBITAL_INCLINATION_DEG, ...
    150.6, ...                  % RAAN (right ascension of ascending node)
    0, ...                      % argument of periapsis
    0, ...                      % true anomaly (starting position)
    "Name",            "RAPID-0", ...
    "OrbitPropagator", "sgp4" ...
);

physicalProperties(rapid_0, ...
    "Mass",            1.0865, ...
    "DragCoefficient", 1, ...
    "DragArea",        0.03, ...
    "SRPArea",         0 ...
);

%% 4. Add UCLA Ground Station
gs_ucla = groundStation(simulation, 34.069, -118.443, "Name", "UCLA");

%% 5. Compute Access (Communication Windows)
disp("Computing access windows — this may take a moment for a 93-day mission...");
ac = access(gs_ucla, rapid_0);
ac.LineColor = [0 1 0];   % green lines during access passes

%% 6. Extract Window Intervals Table
intervals = accessIntervals(ac);

if isempty(intervals)
    disp("No communication windows found. Check orbital parameters or minimum elevation.");
    return
end

%% 7. Add Duration in Minutes Column
intervals.DurationMinutes = intervals.Duration / 60;  % Duration is in seconds

%% 8. Display Summary
fprintf("\n========================================\n");
fprintf("  RAPID-0 <-> UCLA Communication Windows\n");
fprintf("  Mission: %s  to  %s\n", ...
    datestr(MISSION_START, "yyyy-mmm-dd HH:MM"), ...
    datestr(MISSION_END,   "yyyy-mmm-dd HH:MM"));
fprintf("  Min Elevation Filter: %d deg\n", MIN_ELEVATION_DEG);
fprintf("========================================\n\n");

fprintf("Total passes found:     %d\n",   height(intervals));
fprintf("Total contact time:     %.1f hours\n", sum(intervals.Duration) / 3600);
fprintf("Avg pass duration:      %.1f minutes\n", mean(intervals.DurationMinutes));
fprintf("Longest pass:           %.1f minutes\n", max(intervals.DurationMinutes));
fprintf("Shortest pass:          %.1f minutes\n", min(intervals.DurationMinutes));
fprintf("\n");

%% 9. Print Pass Table (first 20 passes)
disp("--- First 20 Passes ---");
disp("  #   Start (UTC)                End (UTC)                  Duration (min)");
disp(repmat('-', 1, 75));
numShow = min(20, height(intervals));
for i = 1:numShow
    fprintf("  %-3d %-26s %-26s %.2f\n", ...
        i, ...
        datestr(intervals.StartTime(i), "yyyy-mmm-dd HH:MM:SS"), ...
        datestr(intervals.EndTime(i),   "yyyy-mmm-dd HH:MM:SS"), ...
        intervals.DurationMinutes(i));
end
if height(intervals) > 20
    fprintf("  ... and %d more passes (see exported table below)\n", height(intervals) - 20);
end

%% 10. Export Full Pass Table to CSV
outputFile = "RAPID0_UCLA_CommWindows.csv";
writetable(intervals(:, ["StartTime","EndTime","DurationMinutes"]), outputFile);
fprintf("\nFull pass table saved to: %s\n", outputFile);

%% 11. Plot: Pass Durations Over Mission Life
figure("Name", "RAPID-0 Pass Durations — UCLA", "NumberTitle", "off");
bar(intervals.StartTime, intervals.DurationMinutes, "FaceColor", [0.2 0.5 0.9]);
xlabel("Date (UTC)");
ylabel("Pass Duration (minutes)");
title("RAPID-0 \leftrightarrow UCLA Communication Windows");
grid on;
yline(mean(intervals.DurationMinutes), "--r", ...
    sprintf("Mean: %.1f min", mean(intervals.DurationMinutes)), ...
    "LabelHorizontalAlignment", "left");
datetick("x", "mmm-dd", "keeplimits");
set(gcf, "Position", [100, 100, 1100, 400]);

%% 12. Plot: Passes Per Day
startDays   = dateshift(intervals.StartTime, "start", "day");
uniqueDays  = unique(startDays);
passesPerDay = arrayfun(@(d) sum(startDays == d), uniqueDays);

figure("Name", "Passes Per Day — UCLA", "NumberTitle", "off");
bar(uniqueDays, passesPerDay, "FaceColor", [0.9 0.4 0.2]);
xlabel("Date (UTC)");
ylabel("Number of Passes");
title("Daily Pass Count: RAPID-0 \leftrightarrow UCLA");
grid on;
yline(mean(passesPerDay), "--k", ...
    sprintf("Mean: %.1f passes/day", mean(passesPerDay)), ...
    "LabelHorizontalAlignment", "left");
datetick("x", "mmm-dd", "keeplimits");
set(gcf, "Position", [100, 550, 1100, 350]);

%% 13. (Optional) Launch 3D Viewer
% Uncomment to open the interactive satellite scenario viewer:
% play(simulation);

disp("Done! Communication window analysis complete.");