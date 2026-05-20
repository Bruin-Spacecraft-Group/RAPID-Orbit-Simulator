MISSION_START = datetime(2028, 6, 1, 8, 0, 0, 0); % 2026 June 01, 08:00:00.0
MISSION_END = MISSION_START + days(93); % 3-month mission life

ORBIT_RADIUS = (6378 + 450) * 1000;
ORBITAL_INCLINATION_DEG = 34.75;

disp(string(py.satellite_simulator.get_string()));

simulation = satelliteScenario(MISSION_START, MISSION_END, 60);
rapid_0 = satellite( ...
    simulation, ...
    ORBIT_RADIUS, ...
    0, ... % eccentricity: how elliptical is our orbit
    ORBITAL_INCLINATION_DEG, ...
    150.6, ... % right ascenscion of ascending node: where does the orbit cross the equator
    0, ... % argument of periapsis: where are we closest to the earth
    0, ... % where in the orbit are we right now
    "Name", "RAPID-0", ...
    "OrbitPropagator", "sgp4" ...
);
% rapid_0 = satellite(simulation, "temp/initial.tle");
physicalProperties(rapid_0, "Mass", 1.0865, "DragCoefficient", 1, "DragArea", 0.03, "SRPArea", 0);
gs_ucla = groundStation(simulation, 34.069, -118.443, Name="UCLA");
access(gs_ucla, rapid_0);
play(simulation);
% while true
%     physicalProperties(rapid_0, "Mass", 1.0865, "DragCoefficient", 1, "DragArea", 0.03, "SRPArea", 0);
% end
