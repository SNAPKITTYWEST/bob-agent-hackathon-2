:- module voxel_world.
:- interface.
:- import_module io.
:- import_module list.
:- import_module map.
:- import_module int.
:- import_module float.
:- import_module string.
:- import_module maybe.
:- import_module pair.
:- type coord
    --->    coord(x :: int, y :: int, z :: int).
:- type voxel_type
    --->    air
    ;       solid
    ;       floor
    ;       water
    ;       obstacle
    ;       resource(resource_type).
:- type resource_type
    --->    oxygen
    ;       power
    ;       food.
:- type entity_id == int.
:- type object_id == int.
:- type orientation
    --->    north
    ;       south
    ;       east
    ;       west
    ;       up
    ;       down.
:- type velocity
    --->    velocity(dx :: float, dy :: float, dz :: float).
:- type entity_state
    --->    idle
    ;       walking
    ;       interacting
    ;       stopped.
:- type entity
    --->    entity(
                id :: entity_id,
                pos :: coord,
                vel :: velocity,
                orient :: orientation,
                state :: entity_state,
                destination :: maybe(coord)
            ).
:- type world_object
    --->    world_object(
                obj_id :: object_id,
                obj_pos :: coord,
                obj_type :: voxel_type,
                obj_state :: object_state
            ).
:- type object_state
    --->    available
    ;       occupied
    ;       depleted.
:- type voxel_map == map(coord, voxel_type).
:- type entity_map == map(entity_id, entity).
:- type object_map == map(object_id, world_object).
:- type world
    --->    world(
                voxels :: voxel_map,
                entities :: entity_map,
                objects :: object_map,
                bounds :: bounds,
                tick_count :: int,
                next_entity_id :: entity_id,
                next_object_id :: object_id
            ).
:- type bounds
    --->    bounds(
                min_x :: int,
                max_x :: int,
                min_y :: int,
                max_y :: int,
                min_z :: int,
                max_z :: int
            ).
:- type action
    --->    move(entity_id, coord)
    ;       stop(entity_id)
    ;       turn(entity_id, orientation)
    ;       interact(entity_id, object_id)
    ;       wait(entity_id).
:- type event
    --->    entity_created(entity_id, coord)
    ;       entity_moved(entity_id, coord, coord)
    ;       entity_stopped(entity_id, coord)
    ;       collision(entity_id, coord, collision_type)
    ;       interaction_started(entity_id, object_id)
    ;       interaction_completed(entity_id, object_id)
    ;       object_created(object_id, coord)
    ;       object_state_changed(object_id, object_state)
    ;       tick_completed(int)
    ;       action_rejected(entity_id, action, world_error).
:- type collision_type
    --->    voxel_collision
    ;       entity_collision(entity_id)
    ;       object_collision(object_id)
    ;       boundary_collision.
:- type world_error
    --->    entity_not_found(entity_id)
    ;       object_not_found(object_id)
    ;       invalid_coordinate(coord)
    ;       blocked_voxel(coord)
    ;       out_of_bounds(coord)
    ;       entity_collision_error(entity_id, entity_id)
    ;       invalid_action(action)
    ;       interaction_failed(entity_id, object_id, string).
:- type world_result(T) == maybe.error(T, world_error).
:- func init_world(bounds) = world.
:- pred create_entity(coord::in, world::in, world::out, entity_id::out) is det.
:- pred remove_entity(entity_id::in, world::in, world::out) is det.
:- pred get_entity(entity_id::in, world::in, world_result(entity)::out) is det.
:- pred update_entity(entity::in, world::in, world::out) is det.
:- pred entity_exists(entity_id::in, world::in) is semidet.
:- pred create_object(coord::in, voxel_type::in, world::in, world::out, object_id::out) is det.
:- pred get_object(object_id::in, world::in, world_result(world_object)::out) is det.
:- pred update_object(world_object::in, world::in, world::out) is det.
:- pred set_voxel(coord::in, voxel_type::in, world::in, world::out) is det.
:- pred get_voxel(coord::in, world::in, voxel_type::out) is det.
:- pred is_walkable(coord::in, world::in) is semidet.
:- pred is_blocked(coord::in, world::in) is semidet.
:- pred is_occupied(coord::in, world::in) is semidet.
:- pred in_bounds(coord::in, bounds::in) is semidet.
:- func coord_add(coord, coord) = coord.
:- func coord_sub(coord, coord) = coord.
:- func coord_distance(coord, coord) = float.
:- pred adjacent(coord::in, coord::in) is semidet.
:- func neighbors(coord) = list(coord).
:- pred apply_action(action::in, world::in, world::out, list(event)::out) is det.
:- pred simulation_tick(list(action)::in, world::in, world::out, list(event)::out) is det.
:- pred move_entity(entity_id::in, coord::in, world::in, world::out, list(event)::out) is det.
:- pred check_collision(coord::in, entity_id::in, world::in, maybe(collision_type)::out) is det.
:- pred calculate_movement(entity::in, float::in, world::in, coord::out, velocity::out) is det.
:- pred interact_with_object(entity_id::in, object_id::in, world::in, world::out, list(event)::out) is det.
:- pred snapshot_world(world::in, string::out) is det.
:- pred restore_world(string::in, world_result(world)::out) is det.
:- implementation.
:- import_module require.
:- import_module math.
:- import_module solutions.
init_world(Bounds) = World :-
    World = world(map.init, map.init, map.init, Bounds, 0, 1, 1).
create_entity(Pos, !World, EntityId) :-
    EntityId = !.World ^ next_entity_id,
    Entity = entity(EntityId, Pos, velocity(0.0, 0.0, 0.0), north, idle, no),
    Entities0 = !.World ^ entities,
    map.set(EntityId, Entity, Entities0, Entities),
    !World ^ entities := Entities,
    !World ^ next_entity_id := EntityId + 1.
remove_entity(EntityId, !World) :-
    Entities0 = !.World ^ entities,
    map.delete(EntityId, Entities0, Entities),
    !World ^ entities := Entities.
get_entity(EntityId, World, Result) :-
    Entities = World ^ entities,
    ( if map.search(Entities, EntityId, Entity) then
        Result = ok(Entity)
    else
        Result = error(entity_not_found(EntityId))
    ).
update_entity(Entity, !World) :-
    EntityId = Entity ^ id,
    Entities0 = !.World ^ entities,
    map.set(EntityId, Entity, Entities0, Entities),
    !World ^ entities := Entities.
entity_exists(EntityId, World) :-
    Entities = World ^ entities,
    map.contains(Entities, EntityId).
create_object(Pos, VoxelType, !World, ObjectId) :-
    ObjectId = !.World ^ next_object_id,
    Obj = world_object(ObjectId, Pos, VoxelType, available),
    Objects0 = !.World ^ objects,
    map.set(ObjectId, Obj, Objects0, Objects),
    !World ^ objects := Objects,
    !World ^ next_object_id := ObjectId + 1.
get_object(ObjectId, World, Result) :-
    Objects = World ^ objects,
    ( if map.search(Objects, ObjectId, Obj) then
        Result = ok(Obj)
    else
        Result = error(object_not_found(ObjectId))
    ).
update_object(Obj, !World) :-
    ObjectId = Obj ^ obj_id,
    Objects0 = !.World ^ objects,
    map.set(ObjectId, Obj, Objects0, Objects),
    !World ^ objects := Objects.
set_voxel(Coord, VoxelType, !World) :-
    Voxels0 = !.World ^ voxels,
    map.set(Coord, VoxelType, Voxels0, Voxels),
    !World ^ voxels := Voxels.
get_voxel(Coord, World, VoxelType) :-
    Voxels = World ^ voxels,
    ( if map.search(Voxels, Coord, VT) then
        VoxelType = VT
    else
        VoxelType = air
    ).
is_walkable(Coord, World) :-
    get_voxel(Coord, World, VoxelType),
    ( VoxelType = air
    ; VoxelType = floor
    ; VoxelType = water
    ),
    not is_occupied(Coord, World).
is_blocked(Coord, World) :-
    get_voxel(Coord, World, VoxelType),
    ( VoxelType = solid
    ; VoxelType = obstacle
    ).
is_occupied(Coord, World) :-
    Entities = World ^ entities,
    map.values(Entities, EntityList),
    list.member(Entity, EntityList),
    Entity ^ pos = Coord.
in_bounds(coord(X, Y, Z), Bounds) :-
    X >= Bounds ^ min_x,
    X =< Bounds ^ max_x,
    Y >= Bounds ^ min_y,
    Y =< Bounds ^ max_y,
    Z >= Bounds ^ min_z,
    Z =< Bounds ^ max_z.
coord_add(coord(X1, Y1, Z1), coord(X2, Y2, Z2)) = coord(X1 + X2, Y1 + Y2, Z1 + Z2).
coord_sub(coord(X1, Y1, Z1), coord(X2, Y2, Z2)) = coord(X1 - X2, Y1 - Y2, Z1 - Z2).
coord_distance(C1, C2) = Distance :-
    Delta = coord_sub(C2, C1),
    DX = float(Delta ^ x),
    DY = float(Delta ^ y),
    DZ = float(Delta ^ z),
    Distance = math.sqrt(DX * DX + DY * DY + DZ * DZ).
adjacent(C1, C2) :-
    Delta = coord_sub(C2, C1),
    AbsX = abs(Delta ^ x),
    AbsY = abs(Delta ^ y),
    AbsZ = abs(Delta ^ z),
    AbsX + AbsY + AbsZ = 1.
neighbors(coord(X, Y, Z)) = [
    coord(X + 1, Y, Z),
    coord(X - 1, Y, Z),
    coord(X, Y + 1, Z),
    coord(X, Y - 1, Z),
    coord(X, Y, Z + 1),
    coord(X, Y, Z - 1)
].
apply_action(Action, !World, Events) :-
    (
        Action = move(EntityId, Dest),
        move_entity(EntityId, Dest, !World, Events)
    ;
        Action = stop(EntityId),
        ( if get_entity(EntityId, !.World, ok(Entity0)) then
            Entity = Entity0 ^ state := stopped,
            Entity1 = Entity ^ vel := velocity(0.0, 0.0, 0.0),
            Entity2 = Entity1 ^ destination := no,
            update_entity(Entity2, !World),
            Events = [entity_stopped(EntityId, Entity2 ^ pos)]
        else
            Events = [action_rejected(EntityId, Action, entity_not_found(EntityId))]
        )
    ;
        Action = turn(EntityId, Orient),
        ( if get_entity(EntityId, !.World, ok(Entity0)) then
            Entity = Entity0 ^ orient := Orient,
            update_entity(Entity, !World),
            Events = []
        else
            Events = [action_rejected(EntityId, Action, entity_not_found(EntityId))]
        )
    ;
        Action = interact(EntityId, ObjectId),
        interact_with_object(EntityId, ObjectId, !World, Events)
    ;
        Action = wait(_EntityId),
        Events = []
    ).
simulation_tick(Actions, !World, AllEvents) :-
    list.foldl2(apply_action, Actions, !World, [], EventsRev),
    list.reverse(EventsRev, ActionEvents),
    TickCount0 = !.World ^ tick_count,
    TickCount = TickCount0 + 1,
    !World ^ tick_count := TickCount,
    TickEvent = tick_completed(TickCount),
    AllEvents = [TickEvent | ActionEvents].
move_entity(EntityId, Dest, !World, Events) :-
    ( if get_entity(EntityId, !.World, ok(Entity0)) then
        Bounds = !.World ^ bounds,
        ( if in_bounds(Dest, Bounds) then
            check_collision(Dest, EntityId, !.World, MaybeCollision),
            (
                MaybeCollision = no,
                OldPos = Entity0 ^ pos,
                Entity1 = Entity0 ^ pos := Dest,
                Entity2 = Entity1 ^ destination := yes(Dest),
                Entity3 = Entity2 ^ state := walking,
                DeltaX = float(Dest ^ x - OldPos ^ x),
                DeltaY = float(Dest ^ y - OldPos ^ y),
                DeltaZ = float(Dest ^ z - OldPos ^ z),
                Entity = Entity3 ^ vel := velocity(DeltaX, DeltaY, DeltaZ),
                update_entity(Entity, !World),
                Events = [entity_moved(EntityId, OldPos, Dest)]
            ;
                MaybeCollision = yes(CollisionType),
                Events = [collision(EntityId, Dest, CollisionType)]
            )
        else
            Events = [action_rejected(EntityId, move(EntityId, Dest), out_of_bounds(Dest))]
        )
    else
        Events = [action_rejected(EntityId, move(EntityId, Dest), entity_not_found(EntityId))]
    ).
check_collision(Coord, EntityId, World, MaybeCollision) :-
    ( if is_blocked(Coord, World) then
        MaybeCollision = yes(voxel_collision)
    else if is_occupied(Coord, World) then
        Entities = World ^ entities,
        map.values(Entities, EntityList),
        ( if
            list.member(OtherEntity, EntityList),
            OtherEntity ^ pos = Coord,
            OtherEntity ^ id \= EntityId
        then
            MaybeCollision = yes(entity_collision(OtherEntity ^ id))
        else
            MaybeCollision = no
        )
    else
        Objects = World ^ objects,
        map.values(Objects, ObjectList),
        ( if
            list.member(Obj, ObjectList),
            Obj ^ obj_pos = Coord
        then
            MaybeCollision = yes(object_collision(Obj ^ obj_id))
        else
            MaybeCollision = no
        )
    ).
calculate_movement(Entity, DeltaTime, World, NewPos, NewVel) :-
    Pos = Entity ^ pos,
    Vel = Entity ^ vel,
    ( if Entity ^ destination = yes(Dest) then
        Direction = coord_sub(Dest, Pos),
        Distance = coord_distance(Pos, Dest),
        ( if Distance > 0.1 then
            Speed = 1.0,
            NormX = float(Direction ^ x) / Distance,
            NormY = float(Direction ^ y) / Distance,
            NormZ = float(Direction ^ z) / Distance,
            DX = NormX * Speed * DeltaTime,
            DY = NormY * Speed * DeltaTime,
            DZ = NormZ * Speed * DeltaTime,
            NewX = Pos ^ x + round_to_int(DX),
            NewY = Pos ^ y + round_to_int(DY),
            NewZ = Pos ^ z + round_to_int(DZ),
            Candidate = coord(NewX, NewY, NewZ),
            Bounds = World ^ bounds,
            ( if in_bounds(Candidate, Bounds), is_walkable(Candidate, World) then
                NewPos = Candidate,
                NewVel = velocity(DX, DY, DZ)
            else
                NewPos = Pos,
                NewVel = velocity(0.0, 0.0, 0.0)
            )
        else
            NewPos = Dest,
            NewVel = velocity(0.0, 0.0, 0.0)
        )
    else
        NewPos = Pos,
        NewVel = velocity(0.0, 0.0, 0.0)
    ).
interact_with_object(EntityId, ObjectId, !World, Events) :-
    ( if
        get_entity(EntityId, !.World, ok(Entity)),
        get_object(ObjectId, !.World, ok(Obj))
    then
        EntityPos = Entity ^ pos,
        ObjPos = Obj ^ obj_pos,
        ( if adjacent(EntityPos, ObjPos) then
            ( if Obj ^ obj_state = available then
                NewObj = Obj ^ obj_state := occupied,
                update_object(NewObj, !World),
                Events = [
                    interaction_started(EntityId, ObjectId),
                    object_state_changed(ObjectId, occupied),
                    interaction_completed(EntityId, ObjectId)
                ]
            else
                Error = interaction_failed(EntityId, ObjectId, "object not available"),
                Events = [action_rejected(EntityId, interact(EntityId, ObjectId), Error)]
            )
        else
            Error = interaction_failed(EntityId, ObjectId, "not adjacent"),
            Events = [action_rejected(EntityId, interact(EntityId, ObjectId), Error)]
        )
    else
        ( if get_entity(EntityId, !.World, error(Err)) then
            Events = [action_rejected(EntityId, interact(EntityId, ObjectId), Err)]
        else
            Events = [action_rejected(EntityId, interact(EntityId, ObjectId), object_not_found(ObjectId))]
        )
    ).
snapshot_world(World, Snapshot) :-
    TickCount = World ^ tick_count,
    NextEntityId = World ^ next_entity_id,
    NextObjectId = World ^ next_object_id,
    Snapshot = string.format("SNAPSHOT:tick=%d,next_eid=%d,next_oid=%d",
        [i(TickCount), i(NextEntityId), i(NextObjectId)]).
restore_world(Snapshot, Result) :-
    ( if string.prefix(Snapshot, "SNAPSHOT:") then
        Result = ok(init_world(bounds(-50, 50, -50, 50, -50, 50)))
    else
        Result = error(invalid_action(wait(0)))
    ).
:- end_module voxel_world.

// Made with Bob
