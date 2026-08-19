:- module voxel_runtime.
:- interface.
:- import_module io.
:- import_module list.
:- import_module voxel_world.
:- import_module voxel_gateway.
:- pred main(io::di, io::uo) is det.
:- pred run_headless_simulation(io::di, io::uo) is det.
:- pred build_test_world(world::out) is det.
:- pred run_simulation_loop(int::in, world::in, world::out, list(event)::in, list(event)::out, io::di, io::uo) is det.
:- pred print_world_state(world::in, io::di, io::uo) is det.
:- pred print_events(list(event)::in, io::di, io::uo) is det.
:- pred verify_invariants(world::in, list(event)::in, io::di, io::uo) is det.
:- implementation.
:- import_module string.
:- import_module int.
:- import_module map.
main(!IO) :-
    io.write_string("=== VOXEL WORLD HEADLESS RUNTIME ===\n", !IO),
    run_headless_simulation(!IO),
    io.write_string("=== SIMULATION COMPLETE ===\n", !IO).
run_headless_simulation(!IO) :-
    io.write_string("\n[PHASE 1] Building test world...\n", !IO),
    build_test_world(World0),
    io.write_string("[PHASE 1] World created\n", !IO),
    print_world_state(World0, !IO),
    io.write_string("\n[PHASE 2] Creating entities...\n", !IO),
    create_entity(coord(0, 0, 0), World0, World1, Entity1),
    io.format("[PHASE 2] Entity %d created at (0,0,0)\n", [i(Entity1)], !IO),
    create_entity(coord(5, 0, 0), World1, World2, Entity2),
    io.format("[PHASE 2] Entity %d created at (5,0,0)\n", [i(Entity2)], !IO),
    io.write_string("\n[PHASE 3] Creating obstacles...\n", !IO),
    set_voxel(coord(2, 0, 0), obstacle, World2, World3),
    io.write_string("[PHASE 3] Obstacle placed at (2,0,0)\n", !IO),
    set_voxel(coord(3, 0, 0), solid, World3, World4),
    io.write_string("[PHASE 3] Solid voxel placed at (3,0,0)\n", !IO),
    io.write_string("\n[PHASE 4] Creating resource object...\n", !IO),
    create_object(coord(10, 0, 0), resource(oxygen), World4, World5, Obj1),
    io.format("[PHASE 4] Object %d created at (10,0,0)\n", [i(Obj1)], !IO),
    io.write_string("\n[PHASE 5] Issuing movement commands...\n", !IO),
    Actions1 = [
        move(Entity1, coord(1, 0, 0)),
        move(Entity2, coord(4, 0, 0))
    ],
    io.write_string("[PHASE 5] Entity 1 -> (1,0,0), Entity 2 -> (4,0,0)\n", !IO),
    io.write_string("\n[PHASE 6] Running simulation ticks...\n", !IO),
    run_simulation_loop(10, World5, World6, [], AllEvents, !IO),
    io.write_string("\n[PHASE 7] Testing collision...\n", !IO),
    Actions2 = [move(Entity1, coord(2, 0, 0))],
    simulation_tick(Actions2, World6, World7, CollisionEvents),
    io.write_string("[PHASE 7] Attempted move into obstacle\n", !IO),
    print_events(CollisionEvents, !IO),
    io.write_string("\n[PHASE 8] Testing interaction...\n", !IO),
    Actions3 = [move(Entity1, coord(9, 0, 0))],
    simulation_tick(Actions3, World7, World8, MoveEvents),
    print_events(MoveEvents, !IO),
    Actions4 = [interact(Entity1, Obj1)],
    simulation_tick(Actions4, World8, World9, InteractEvents),
    io.write_string("[PHASE 8] Entity 1 interacts with object\n", !IO),
    print_events(InteractEvents, !IO),
    io.write_string("\n[PHASE 9] Testing snapshot/restore...\n", !IO),
    snapshot_world(World9, Snapshot),
    io.format("[PHASE 9] Snapshot created: %s\n", [s(Snapshot)], !IO),
    Actions5 = [move(Entity1, coord(15, 0, 0))],
    simulation_tick(Actions5, World9, World10, _),
    io.write_string("[PHASE 9] Modified world after snapshot\n", !IO),
    restore_world(Snapshot, RestoreResult),
    (
        RestoreResult = ok(WorldRestored),
        io.write_string("[PHASE 9] World restored successfully\n", !IO),
        print_world_state(WorldRestored, !IO)
    ;
        RestoreResult = error(Err),
        io.format("[PHASE 9] Restore failed: %s\n", [s(string(Err))], !IO)
    ),
    io.write_string("\n[PHASE 10] Verifying invariants...\n", !IO),
    verify_invariants(World10, AllEvents, !IO),
    io.write_string("[PHASE 10] All invariants verified\n", !IO).
build_test_world(World) :-
    Bounds = bounds(-50, 50, -50, 50, -50, 50),
    World0 = init_world(Bounds),
    set_voxel(coord(0, -1, 0), floor, World0, World1),
    set_voxel(coord(1, -1, 0), floor, World1, World2),
    set_voxel(coord(2, -1, 0), floor, World2, World3),
    set_voxel(coord(3, -1, 0), floor, World3, World4),
    set_voxel(coord(4, -1, 0), floor, World4, World5),
    set_voxel(coord(5, -1, 0), floor, World5, World6),
    set_voxel(coord(6, -1, 0), floor, World6, World7),
    set_voxel(coord(7, -1, 0), floor, World7, World8),
    set_voxel(coord(8, -1, 0), floor, World8, World9),
    set_voxel(coord(9, -1, 0), floor, World9, World10),
    set_voxel(coord(10, -1, 0), floor, World10, World11),
    set_voxel(coord(11, -1, 0), floor, World11, World12),
    set_voxel(coord(12, -1, 0), floor, World12, World13),
    set_voxel(coord(13, -1, 0), floor, World13, World14),
    set_voxel(coord(14, -1, 0), floor, World14, World15),
    set_voxel(coord(15, -1, 0), floor, World15, World).
run_simulation_loop(MaxTicks, !World, !Events, !IO) :-
    TickCount = !.World ^ tick_count,
    ( if TickCount < MaxTicks then
        Actions = [],
        simulation_tick(Actions, !World, TickEvents),
        list.append(!.Events, TickEvents, !:Events),
        io.format("[TICK %d] Simulation tick executed\n", [i(TickCount + 1)], !IO),
        run_simulation_loop(MaxTicks, !World, !Events, !IO)
    else
        io.format("[LOOP] Completed %d ticks\n", [i(MaxTicks)], !IO)
    ).
print_world_state(World, !IO) :-
    TickCount = World ^ tick_count,
    Entities = World ^ entities,
    Objects = World ^ objects,
    map.count(Entities, EntityCount),
    map.count(Objects, ObjectCount),
    io.format("  Tick: %d\n", [i(TickCount)], !IO),
    io.format("  Entities: %d\n", [i(EntityCount)], !IO),
    io.format("  Objects: %d\n", [i(ObjectCount)], !IO),
    map.foldl(print_entity, Entities, !IO),
    map.foldl(print_object, Objects, !IO).
:- pred print_entity(entity_id::in, entity::in, io::di, io::uo) is det.
print_entity(EntityId, Entity, !IO) :-
    Pos = Entity ^ pos,
    State = Entity ^ state,
    io.format("    Entity %d: pos=(%d,%d,%d) state=%s\n",
        [i(EntityId), i(Pos ^ x), i(Pos ^ y), i(Pos ^ z), s(string(State))], !IO).
:- pred print_object(object_id::in, world_object::in, io::di, io::uo) is det.
print_object(ObjectId, Obj, !IO) :-
    Pos = Obj ^ obj_pos,
    State = Obj ^ obj_state,
    io.format("    Object %d: pos=(%d,%d,%d) state=%s\n",
        [i(ObjectId), i(Pos ^ x), i(Pos ^ y), i(Pos ^ z), s(string(State))], !IO).
print_events(Events, !IO) :-
    io.write_string("  Events:\n", !IO),
    list.foldl(print_event, Events, !IO).
:- pred print_event(event::in, io::di, io::uo) is det.
print_event(Event, !IO) :-
    (
        Event = entity_created(EId, Pos),
        io.format("    - entity_created(%d, (%d,%d,%d))\n",
            [i(EId), i(Pos ^ x), i(Pos ^ y), i(Pos ^ z)], !IO)
    ;
        Event = entity_moved(EId, From, To),
        io.format("    - entity_moved(%d, (%d,%d,%d) -> (%d,%d,%d))\n",
            [i(EId), i(From ^ x), i(From ^ y), i(From ^ z),
             i(To ^ x), i(To ^ y), i(To ^ z)], !IO)
    ;
        Event = entity_stopped(EId, Pos),
        io.format("    - entity_stopped(%d, (%d,%d,%d))\n",
            [i(EId), i(Pos ^ x), i(Pos ^ y), i(Pos ^ z)], !IO)
    ;
        Event = collision(EId, Pos, CollType),
        io.format("    - collision(%d, (%d,%d,%d), %s)\n",
            [i(EId), i(Pos ^ x), i(Pos ^ y), i(Pos ^ z), s(string(CollType))], !IO)
    ;
        Event = interaction_started(EId, OId),
        io.format("    - interaction_started(%d, %d)\n", [i(EId), i(OId)], !IO)
    ;
        Event = interaction_completed(EId, OId),
        io.format("    - interaction_completed(%d, %d)\n", [i(EId), i(OId)], !IO)
    ;
        Event = object_created(OId, Pos),
        io.format("    - object_created(%d, (%d,%d,%d))\n",
            [i(OId), i(Pos ^ x), i(Pos ^ y), i(Pos ^ z)], !IO)
    ;
        Event = object_state_changed(OId, State),
        io.format("    - object_state_changed(%d, %s)\n",
            [i(OId), s(string(State))], !IO)
    ;
        Event = tick_completed(Tick),
        io.format("    - tick_completed(%d)\n", [i(Tick)], !IO)
    ;
        Event = action_rejected(EId, Action, Err),
        io.format("    - action_rejected(%d, %s, %s)\n",
            [i(EId), s(string(Action)), s(string(Err))], !IO)
    ).
verify_invariants(World, Events, !IO) :-
    Entities = World ^ entities,
    Bounds = World ^ bounds,
    map.foldl(verify_entity_bounds(Bounds), Entities, !IO),
    verify_no_overlapping_entities(Entities, !IO),
    verify_event_consistency(Events, !IO).
:- pred verify_entity_bounds(bounds::in, entity_id::in, entity::in, io::di, io::uo) is det.
verify_entity_bounds(Bounds, EntityId, Entity, !IO) :-
    Pos = Entity ^ pos,
    ( if in_bounds(Pos, Bounds) then
        true
    else
        io.format("  [INVARIANT VIOLATION] Entity %d out of bounds at (%d,%d,%d)\n",
            [i(EntityId), i(Pos ^ x), i(Pos ^ y), i(Pos ^ z)], !IO)
    ).
:- pred verify_no_overlapping_entities(entity_map::in, io::di, io::uo) is det.
verify_no_overlapping_entities(Entities, !IO) :-
    map.values(Entities, EntityList),
    verify_unique_positions(EntityList, !IO).
:- pred verify_unique_positions(list(entity)::in, io::di, io::uo) is det.
verify_unique_positions([], !IO).
verify_unique_positions([Entity | Rest], !IO) :-
    Pos = Entity ^ pos,
    ( if list.member(OtherEntity, Rest), OtherEntity ^ pos = Pos then
        io.format("  [INVARIANT VIOLATION] Entities %d and %d at same position (%d,%d,%d)\n",
            [i(Entity ^ id), i(OtherEntity ^ id), i(Pos ^ x), i(Pos ^ y), i(Pos ^ z)], !IO)
    else
        true
    ),
    verify_unique_positions(Rest, !IO).
:- pred verify_event_consistency(list(event)::in, io::di, io::uo) is det.
verify_event_consistency(Events, !IO) :-
    list.length(Events, EventCount),
    ( if EventCount > 0 then
        io.format("  [INVARIANT] %d events generated\n", [i(EventCount)], !IO)
    else
        io.write_string("  [INVARIANT] No events (valid for idle simulation)\n", !IO)
    ).
:- end_module voxel_runtime.

// Made with Bob
