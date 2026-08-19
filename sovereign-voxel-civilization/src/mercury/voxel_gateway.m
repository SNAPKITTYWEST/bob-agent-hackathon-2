:- module voxel_gateway.
:- interface.
:- import_module io.
:- import_module list.
:- import_module string.
:- import_module maybe.
:- import_module voxel_world.
:- type gateway_request
    --->    get_world_state
    ;       get_entity_state(entity_id)
    ;       get_object_state(object_id)
    ;       get_voxel_at(coord)
    ;       set_voxel_at(coord, voxel_type)
    ;       create_entity_at(coord)
    ;       remove_entity_req(entity_id)
    ;       create_object_at(coord, voxel_type)
    ;       execute_action(action)
    ;       execute_tick(list(action))
    ;       take_snapshot
    ;       restore_snapshot(string)
    ;       health_check.
:- type gateway_response
    --->    world_state_response(world)
    ;       entity_state_response(world_result(entity))
    ;       object_state_response(world_result(world_object))
    ;       voxel_response(voxel_type)
    ;       voxel_set_response
    ;       entity_created_response(entity_id)
    ;       entity_removed_response
    ;       object_created_response(object_id)
    ;       action_executed_response(list(event))
    ;       tick_executed_response(list(event))
    ;       snapshot_response(string)
    ;       restore_response(world_result(world))
    ;       health_response(string)
    ;       error_response(gateway_error).
:- type gateway_error
    --->    invalid_request(string)
    ;       world_error_gateway(world_error)
    ;       internal_error(string).
:- pred process_request(gateway_request::in, world::in, world::out, gateway_response::out) is det.
:- pred handle_get_world_state(world::in, gateway_response::out) is det.
:- pred handle_get_entity_state(entity_id::in, world::in, gateway_response::out) is det.
:- pred handle_get_object_state(object_id::in, world::in, gateway_response::out) is det.
:- pred handle_get_voxel(coord::in, world::in, gateway_response::out) is det.
:- pred handle_set_voxel(coord::in, voxel_type::in, world::in, world::out, gateway_response::out) is det.
:- pred handle_create_entity(coord::in, world::in, world::out, gateway_response::out) is det.
:- pred handle_remove_entity(entity_id::in, world::in, world::out, gateway_response::out) is det.
:- pred handle_create_object(coord::in, voxel_type::in, world::in, world::out, gateway_response::out) is det.
:- pred handle_execute_action(action::in, world::in, world::out, gateway_response::out) is det.
:- pred handle_execute_tick(list(action)::in, world::in, world::out, gateway_response::out) is det.
:- pred handle_snapshot(world::in, gateway_response::out) is det.
:- pred handle_restore(string::in, gateway_response::out) is det.
:- pred handle_health_check(gateway_response::out) is det.
:- implementation.
process_request(Request, !World, Response) :-
    (
        Request = get_world_state,
        handle_get_world_state(!.World, Response)
    ;
        Request = get_entity_state(EntityId),
        handle_get_entity_state(EntityId, !.World, Response)
    ;
        Request = get_object_state(ObjectId),
        handle_get_object_state(ObjectId, !.World, Response)
    ;
        Request = get_voxel_at(Coord),
        handle_get_voxel(Coord, !.World, Response)
    ;
        Request = set_voxel_at(Coord, VoxelType),
        handle_set_voxel(Coord, VoxelType, !World, Response)
    ;
        Request = create_entity_at(Coord),
        handle_create_entity(Coord, !World, Response)
    ;
        Request = remove_entity_req(EntityId),
        handle_remove_entity(EntityId, !World, Response)
    ;
        Request = create_object_at(Coord, VoxelType),
        handle_create_object(Coord, VoxelType, !World, Response)
    ;
        Request = execute_action(Action),
        handle_execute_action(Action, !World, Response)
    ;
        Request = execute_tick(Actions),
        handle_execute_tick(Actions, !World, Response)
    ;
        Request = take_snapshot,
        handle_snapshot(!.World, Response)
    ;
        Request = restore_snapshot(Snapshot),
        handle_restore(Snapshot, Response)
    ;
        Request = health_check,
        handle_health_check(Response)
    ).
handle_get_world_state(World, Response) :-
    Response = world_state_response(World).
handle_get_entity_state(EntityId, World, Response) :-
    get_entity(EntityId, World, Result),
    Response = entity_state_response(Result).
handle_get_object_state(ObjectId, World, Response) :-
    get_object(ObjectId, World, Result),
    Response = object_state_response(Result).
handle_get_voxel(Coord, World, Response) :-
    get_voxel(Coord, World, VoxelType),
    Response = voxel_response(VoxelType).
handle_set_voxel(Coord, VoxelType, !World, Response) :-
    set_voxel(Coord, VoxelType, !World),
    Response = voxel_set_response.
handle_create_entity(Coord, !World, Response) :-
    create_entity(Coord, !World, EntityId),
    Response = entity_created_response(EntityId).
handle_remove_entity(EntityId, !World, Response) :-
    remove_entity(EntityId, !World),
    Response = entity_removed_response.
handle_create_object(Coord, VoxelType, !World, Response) :-
    create_object(Coord, VoxelType, !World, ObjectId),
    Response = object_created_response(ObjectId).
handle_execute_action(Action, !World, Response) :-
    apply_action(Action, !World, Events),
    Response = action_executed_response(Events).
handle_execute_tick(Actions, !World, Response) :-
    simulation_tick(Actions, !World, Events),
    Response = tick_executed_response(Events).
handle_snapshot(World, Response) :-
    snapshot_world(World, Snapshot),
    Response = snapshot_response(Snapshot).
handle_restore(Snapshot, Response) :-
    restore_world(Snapshot, Result),
    Response = restore_response(Result).
handle_health_check(Response) :-
    Response = health_response("gateway operational").
:- end_module voxel_gateway.

// Made with Bob
