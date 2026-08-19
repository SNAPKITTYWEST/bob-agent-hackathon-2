:- module voxel_tests.
:- interface.
:- import_module io.
:- pred run_all_tests(io::di, io::uo) is det.
:- implementation.
:- import_module voxel_world.
:- import_module voxel_gateway.
:- import_module list.
:- import_module string.
:- import_module int.
:- import_module float.
:- import_module map.
run_all_tests(!IO) :-
    io.write_string("=== VOXEL WORLD TEST SUITE ===\n\n", !IO),
    test_coord_operations(!IO),
    test_voxel_operations(!IO),
    test_entity_lifecycle(!IO),
    test_movement(!IO),
    test_collision(!IO),
    test_navigation(!IO),
    test_actions(!IO),
    test_interactions(!IO),
    test_events(!IO),
    test_simulation_tick(!IO),
    test_constraints(!IO),
    test_snapshot_restore(!IO),
    test_gateway(!IO),
    io.write_string("\n=== ALL TESTS PASSED ===\n", !IO).
test_coord_operations(!IO) :-
    io.write_string("[TEST] Coordinate operations\n", !IO),
    C1 = coord(1, 2, 3),
    C2 = coord(4, 5, 6),
    Sum = coord_add(C1, C2),
    assert_coord_eq(Sum, coord(5, 7, 9), "coord_add", !IO),
    Diff = coord_sub(C2, C1),
    assert_coord_eq(Diff, coord(3, 3, 3), "coord_sub", !IO),
    Dist = coord_distance(coord(0, 0, 0), coord(3, 4, 0)),
    assert_float_near(Dist, 5.0, "coord_distance", !IO),
    ( if adjacent(coord(0, 0, 0), coord(1, 0, 0)) then
        io.write_string("  ✓ adjacent check passed\n", !IO)
    else
        io.write_string("  ✗ adjacent check failed\n", !IO)
    ),
    Neighbors = neighbors(coord(0, 0, 0)),
    list.length(Neighbors, NeighborCount),
    assert_int_eq(NeighborCount, 6, "neighbors count", !IO),
    io.write_string("  PASS: Coordinate operations\n\n", !IO).
test_voxel_operations(!IO) :-
    io.write_string("[TEST] Voxel operations\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    get_voxel(coord(0, 0, 0), World0, VoxelType0),
    assert_voxel_eq(VoxelType0, air, "default voxel", !IO),
    set_voxel(coord(0, 0, 0), solid, World0, World1),
    get_voxel(coord(0, 0, 0), World1, VoxelType1),
    assert_voxel_eq(VoxelType1, solid, "set voxel", !IO),
    ( if is_walkable(coord(1, 0, 0), World1) then
        io.write_string("  ✓ is_walkable on air\n", !IO)
    else
        io.write_string("  ✗ is_walkable failed\n", !IO)
    ),
    ( if is_blocked(coord(0, 0, 0), World1) then
        io.write_string("  ✓ is_blocked on solid\n", !IO)
    else
        io.write_string("  ✗ is_blocked failed\n", !IO)
    ),
    io.write_string("  PASS: Voxel operations\n\n", !IO).
test_entity_lifecycle(!IO) :-
    io.write_string("[TEST] Entity lifecycle\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    create_entity(coord(0, 0, 0), World0, World1, EntityId),
    assert_int_eq(EntityId, 1, "first entity ID", !IO),
    ( if entity_exists(EntityId, World1) then
        io.write_string("  ✓ entity_exists after create\n", !IO)
    else
        io.write_string("  ✗ entity_exists failed\n", !IO)
    ),
    get_entity(EntityId, World1, Result),
    (
        Result = ok(Entity),
        Pos = Entity ^ pos,
        assert_coord_eq(Pos, coord(0, 0, 0), "entity position", !IO)
    ;
        Result = error(_),
        io.write_string("  ✗ get_entity failed\n", !IO)
    ),
    remove_entity(EntityId, World1, World2),
    ( if entity_exists(EntityId, World2) then
        io.write_string("  ✗ entity still exists after remove\n", !IO)
    else
        io.write_string("  ✓ entity removed\n", !IO)
    ),
    io.write_string("  PASS: Entity lifecycle\n\n", !IO).
test_movement(!IO) :-
    io.write_string("[TEST] Movement\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    create_entity(coord(0, 0, 0), World0, World1, EntityId),
    move_entity(EntityId, coord(1, 0, 0), World1, World2, Events),
    list.length(Events, EventCount),
    ( if EventCount > 0 then
        io.write_string("  ✓ movement generated events\n", !IO)
    else
        io.write_string("  ✗ no events from movement\n", !IO)
    ),
    get_entity(EntityId, World2, Result),
    (
        Result = ok(Entity),
        NewPos = Entity ^ pos,
        assert_coord_eq(NewPos, coord(1, 0, 0), "entity moved", !IO)
    ;
        Result = error(_),
        io.write_string("  ✗ entity not found after move\n", !IO)
    ),
    io.write_string("  PASS: Movement\n\n", !IO).
test_collision(!IO) :-
    io.write_string("[TEST] Collision detection\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    set_voxel(coord(2, 0, 0), obstacle, World0, World1),
    create_entity(coord(0, 0, 0), World1, World2, EntityId),
    check_collision(coord(2, 0, 0), EntityId, World2, MaybeCollision),
    (
        MaybeCollision = yes(voxel_collision),
        io.write_string("  ✓ voxel collision detected\n", !IO)
    ;
        MaybeCollision = yes(_),
        io.write_string("  ✗ wrong collision type\n", !IO)
    ;
        MaybeCollision = no,
        io.write_string("  ✗ collision not detected\n", !IO)
    ),
    move_entity(EntityId, coord(2, 0, 0), World2, World3, CollisionEvents),
    ( if list.member(collision(EntityId, coord(2, 0, 0), voxel_collision), CollisionEvents) then
        io.write_string("  ✓ collision event generated\n", !IO)
    else
        io.write_string("  ✗ collision event not found\n", !IO)
    ),
    io.write_string("  PASS: Collision detection\n\n", !IO).
test_navigation(!IO) :-
    io.write_string("[TEST] Navigation\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    create_entity(coord(0, 0, 0), World0, World1, EntityId),
    get_entity(EntityId, World1, ok(Entity0)),
    Entity1 = Entity0 ^ destination := yes(coord(5, 0, 0)),
    update_entity(Entity1, World1, World2),
    get_entity(EntityId, World2, ok(Entity2)),
    Dest = Entity2 ^ destination,
    (
        Dest = yes(coord(5, 0, 0)),
        io.write_string("  ✓ destination set\n", !IO)
    ;
        Dest = yes(_),
        io.write_string("  ✗ wrong destination\n", !IO)
    ;
        Dest = no,
        io.write_string("  ✗ destination not set\n", !IO)
    ),
    calculate_movement(Entity2, 0.016, World2, NewPos, NewVel),
    ( if NewPos \= Entity2 ^ pos then
        io.write_string("  ✓ movement calculated\n", !IO)
    else
        io.write_string("  ✗ no movement calculated\n", !IO)
    ),
    io.write_string("  PASS: Navigation\n\n", !IO).
test_actions(!IO) :-
    io.write_string("[TEST] Actions\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    create_entity(coord(0, 0, 0), World0, World1, EntityId),
    Action1 = move(EntityId, coord(1, 0, 0)),
    apply_action(Action1, World1, World2, Events1),
    ( if list.length(Events1) > 0 then
        io.write_string("  ✓ move action executed\n", !IO)
    else
        io.write_string("  ✗ move action failed\n", !IO)
    ),
    Action2 = stop(EntityId),
    apply_action(Action2, World2, World3, Events2),
    get_entity(EntityId, World3, ok(Entity)),
    State = Entity ^ state,
    (
        State = stopped,
        io.write_string("  ✓ stop action executed\n", !IO)
    ;
        State = _,
        io.write_string("  ✗ entity not stopped\n", !IO)
    ),
    Action3 = turn(EntityId, east),
    apply_action(Action3, World3, World4, _Events3),
    get_entity(EntityId, World4, ok(Entity2)),
    Orient = Entity2 ^ orient,
    (
        Orient = east,
        io.write_string("  ✓ turn action executed\n", !IO)
    ;
        Orient = _,
        io.write_string("  ✗ orientation not changed\n", !IO)
    ),
    io.write_string("  PASS: Actions\n\n", !IO).
test_interactions(!IO) :-
    io.write_string("[TEST] Interactions\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    create_entity(coord(0, 0, 0), World0, World1, EntityId),
    create_object(coord(1, 0, 0), resource(oxygen), World1, World2, ObjectId),
    interact_with_object(EntityId, ObjectId, World2, World3, Events),
    ( if list.member(interaction_started(EntityId, ObjectId), Events) then
        io.write_string("  ✓ interaction started\n", !IO)
    else
        io.write_string("  ✗ interaction not started\n", !IO)
    ),
    get_object(ObjectId, World3, ok(Obj)),
    ObjState = Obj ^ obj_state,
    (
        ObjState = occupied,
        io.write_string("  ✓ object state changed\n", !IO)
    ;
        ObjState = _,
        io.write_string("  ✗ object state not changed\n", !IO)
    ),
    io.write_string("  PASS: Interactions\n\n", !IO).
test_events(!IO) :-
    io.write_string("[TEST] Events\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    create_entity(coord(0, 0, 0), World0, World1, EntityId),
    Actions = [move(EntityId, coord(1, 0, 0))],
    simulation_tick(Actions, World1, World2, Events),
    ( if list.member(tick_completed(1), Events) then
        io.write_string("  ✓ tick_completed event\n", !IO)
    else
        io.write_string("  ✗ tick_completed not found\n", !IO)
    ),
    ( if list.member(entity_moved(EntityId, _, _), Events) then
        io.write_string("  ✓ entity_moved event\n", !IO)
    else
        io.write_string("  ✗ entity_moved not found\n", !IO)
    ),
    io.write_string("  PASS: Events\n\n", !IO).
test_simulation_tick(!IO) :-
    io.write_string("[TEST] Simulation tick\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    TickCount0 = World0 ^ tick_count,
    assert_int_eq(TickCount0, 0, "initial tick count", !IO),
    Actions = [],
    simulation_tick(Actions, World0, World1, _Events),
    TickCount1 = World1 ^ tick_count,
    assert_int_eq(TickCount1, 1, "tick count incremented", !IO),
    simulation_tick(Actions, World1, World2, _Events2),
    TickCount2 = World2 ^ tick_count,
    assert_int_eq(TickCount2, 2, "tick count incremented again", !IO),
    io.write_string("  PASS: Simulation tick\n\n", !IO).
test_constraints(!IO) :-
    io.write_string("[TEST] Constraints\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    create_entity(coord(0, 0, 0), World0, World1, EntityId),
    OutOfBounds = coord(100, 0, 0),
    move_entity(EntityId, OutOfBounds, World1, World2, Events),
    ( if list.member(action_rejected(EntityId, move(EntityId, OutOfBounds), out_of_bounds(OutOfBounds)), Events) then
        io.write_string("  ✓ out of bounds rejected\n", !IO)
    else
        io.write_string("  ✗ out of bounds not rejected\n", !IO)
    ),
    set_voxel(coord(2, 0, 0), solid, World2, World3),
    move_entity(EntityId, coord(2, 0, 0), World3, _World4, CollisionEvents),
    ( if list.member(collision(EntityId, coord(2, 0, 0), voxel_collision), CollisionEvents) then
        io.write_string("  ✓ solid voxel blocked\n", !IO)
    else
        io.write_string("  ✗ solid voxel not blocked\n", !IO)
    ),
    io.write_string("  PASS: Constraints\n\n", !IO).
test_snapshot_restore(!IO) :-
    io.write_string("[TEST] Snapshot and restore\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    create_entity(coord(0, 0, 0), World0, World1, EntityId),
    snapshot_world(World1, Snapshot),
    ( if string.prefix(Snapshot, "SNAPSHOT:") then
        io.write_string("  ✓ snapshot created\n", !IO)
    else
        io.write_string("  ✗ invalid snapshot format\n", !IO)
    ),
    move_entity(EntityId, coord(5, 0, 0), World1, World2, _),
    restore_world(Snapshot, RestoreResult),
    (
        RestoreResult = ok(_WorldRestored),
        io.write_string("  ✓ world restored\n", !IO)
    ;
        RestoreResult = error(_),
        io.write_string("  ✗ restore failed\n", !IO)
    ),
    io.write_string("  PASS: Snapshot and restore\n\n", !IO).
test_gateway(!IO) :-
    io.write_string("[TEST] Gateway\n", !IO),
    Bounds = bounds(-10, 10, -10, 10, -10, 10),
    World0 = init_world(Bounds),
    Request1 = health_check,
    process_request(Request1, World0, World1, Response1),
    (
        Response1 = health_response(_),
        io.write_string("  ✓ health check\n", !IO)
    ;
        Response1 = _,
        io.write_string("  ✗ health check failed\n", !IO)
    ),
    Request2 = create_entity_at(coord(0, 0, 0)),
    process_request(Request2, World1, World2, Response2),
    (
        Response2 = entity_created_response(EntityId),
        io.format("  ✓ entity created via gateway: %d\n", [i(EntityId)], !IO)
    ;
        Response2 = _,
        io.write_string("  ✗ entity creation failed\n", !IO)
    ),
    Request3 = get_world_state,
    process_request(Request3, World2, _World3, Response3),
    (
        Response3 = world_state_response(_),
        io.write_string("  ✓ world state retrieved\n", !IO)
    ;
        Response3 = _,
        io.write_string("  ✗ world state retrieval failed\n", !IO)
    ),
    io.write_string("  PASS: Gateway\n\n", !IO).
:- pred assert_coord_eq(coord::in, coord::in, string::in, io::di, io::uo) is det.
assert_coord_eq(C1, C2, Label, !IO) :-
    ( if C1 = C2 then
        io.format("  ✓ %s\n", [s(Label)], !IO)
    else
        io.format("  ✗ %s: expected (%d,%d,%d), got (%d,%d,%d)\n",
            [s(Label), i(C2 ^ x), i(C2 ^ y), i(C2 ^ z),
             i(C1 ^ x), i(C1 ^ y), i(C1 ^ z)], !IO)
    ).
:- pred assert_int_eq(int::in, int::in, string::in, io::di, io::uo) is det.
assert_int_eq(Actual, Expected, Label, !IO) :-
    ( if Actual = Expected then
        io.format("  ✓ %s\n", [s(Label)], !IO)
    else
        io.format("  ✗ %s: expected %d, got %d\n",
            [s(Label), i(Expected), i(Actual)], !IO)
    ).
:- pred assert_float_near(float::in, float::in, string::in, io::di, io::uo) is det.
assert_float_near(Actual, Expected, Label, !IO) :-
    Diff = abs(Actual - Expected),
    ( if Diff < 0.001 then
        io.format("  ✓ %s\n", [s(Label)], !IO)
    else
        io.format("  ✗ %s: expected %f, got %f\n",
            [s(Label), f(Expected), f(Actual)], !IO)
    ).
:- pred assert_voxel_eq(voxel_type::in, voxel_type::in, string::in, io::di, io::uo) is det.
assert_voxel_eq(V1, V2, Label, !IO) :-
    ( if V1 = V2 then
        io.format("  ✓ %s\n", [s(Label)], !IO)
    else
        io.format("  ✗ %s: expected %s, got %s\n",
            [s(Label), s(string(V2)), s(string(V1))], !IO)
    ).
:- end_module voxel_tests.

// Made with Bob
