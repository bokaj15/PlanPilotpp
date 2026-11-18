#const horizon=1.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Horizon, must be defined externally
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

time(0..horizon).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Establish initial state
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

holds(Variable, Value, 0) :- initialState(Variable, Value).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Compute derived predicates
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% conjunctive preconditions
satisfied(DerivedPredicate, type(and), T) :- derivedPredicate(DerivedPredicate, type(and)), holds(Variable, Value, T) : precondition(DerivedPredicate, type(and), Variable, Value); time(T).

% disjunctive preconditions
satisfied(DerivedPredicate, type(or), T) :- precondition(DerivedPredicate, type(or), Variable, Value), holds(Variable, Value, T), time(T).

holds(DerivedVariable, Value, T) :- satisfied(DerivedPredicate, Type, T), postcondition(DerivedPredicate, Type, effect(unconditional), DerivedVariable, Value).

holds(derivedVariable(DerivedVariable), value(DerivedVariable, false), T) :- derivedVariable(DerivedVariable), not holds(derivedVariable(DerivedVariable), value(DerivedVariable, true), T), time(T).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Perform actions
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

0 {occurs(Action, T) : action(Action)} 1 :- time(T), T > 0.

% Check preconditions
:- occurs(Action, T), applied_precondition(Action, Variable, Value), not holds(Variable, Value, T - 1).

% Apply effects
caused(Variable, Value, T) :-
	occurs(Action, T),
	applied_postcondition(Action, Effect, Variable, Value),
	holds(VariablePre, ValuePre, T - 1) : applied_postcondition(Effect, VariablePre, ValuePre).

applied_precondition(Action, Variable, Value) :-
	precondition(Action, Variable, Value), not deleted_precondition(Action, Variable, Value).
	
applied_precondition(Action, Variable, Value) :-
    added_precondition(Action, Variable, Value).
	
applied_postcondition(Action, Effect, Variable, Value) :-
	postcondition(Action, Effect, Variable, Value),
	not deleted_postcondition(Action, Effect, Variable, Value).

applied_postcondition(Action, effect(unconditional), Variable, Value) :-
	added_effect(Action, Variable, Value).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Inertia rules
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

modified(Variable, T) :- caused(Variable, Value, T).

holds(Variable, Value, T) :- caused(Variable, Value, T).
holds(variable(V), Value, T) :- holds(variable(V), Value, T - 1), not modified(variable(V), T), time(T).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Variables and mutex groups
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Check that variables have unique values
:- variable(Variable), not 1 {holds(Variable, Value, T) : contains(Variable, Value)} 1, time(T).

% Check mutexes
:- mutexGroup(MutexGroup), not {holds(Variable, Value, T) : contains(MutexGroup, Variable, Value)} 1, time(T).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Verify that goal is met
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

:- goal(Variable, Value), not holds(Variable, Value, horizon).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Shows all 'occurs' atoms.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

#show occurs/2.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Repair encoding
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

repair(delete_precondition("load-truck",("airport", par3),true)).


deleted_precondition(action(("load-truck", X1, X2, X3)), variable(("airport", X3)), 
	value(variable(("airport", X3)), true)) :- action(action(("load-truck", X1, X2, X3))), enabled(delete_precondition("load-truck",("airport", par3),true)).


% choose any subset of repairs
{enabled(R) : repair(R)}.

#show enabled/1.


%---------------------------------------
% domain
%---------------------------------------

% utils
boolean(true).
boolean(false).

% types
type(type("location")).
inherits(type("location"), type("object")).
type(type("locatable")).
inherits(type("locatable"), type("object")).
type(type("object")).
type(type("package")).
inherits(type("package"), type("locatable")).
type(type("truck")).
inherits(type("truck"), type("locatable")).
type(type("airplane")).
inherits(type("airplane"), type("locatable")).
type(type("airport")).
inherits(type("airport"), type("location")).
type(type("city")).
inherits(type("city"), type("location")).

has(X, type(T2)) :- has(X, type(T1)), inherits(type(T1), type(T2)).

% variables
variable(variable(("at", X1, X2))) :- has(X1, type("locatable")), has(X2, type("location")).
variable(variable(("in", X1, X2))) :- has(X1, type("locatable")), has(X2, type("locatable")).
variable(variable(("in-city", X1, X2))) :- has(X1, type("location")), has(X2, type("location")).
variable(variable(("road", X1, X2))) :- has(X1, type("location")), has(X2, type("location")).
variable(variable(("airport", X1))) :- has(X1, type("location")).

contains(X, value(X, B)) :- variable(X), boolean(B).

% actions
action(action(("load-truck", X1, X2, X3))) :- has(X1, type("package")), has(X2, type("truck")), has(X3, type("location")).
precondition(action(("load-truck", X1, X2, X3)), variable(("at", X2, X3)), value(variable(("at", X2, X3)), true)) :- action(action(("load-truck", X1, X2, X3))).
precondition(action(("load-truck", X1, X2, X3)), variable(("at", X1, X3)), value(variable(("at", X1, X3)), true)) :- action(action(("load-truck", X1, X2, X3))).

%Lets imagine that the domain has this precondition, that should be removed in order to make the task solvable
%The truck can only load packages if the location is an airport
%All preconditions are enabled by default, as long as their deletion is not enabled
precondition(action(("load-truck", X1, X2, X3)), variable(("airport", X3)), value(variable(("airport", X3)), true)) :- action(action(("load-truck", X1, X2, X3))).

postcondition(action(("load-truck", X1, X2, X3)), effect(unconditional), variable(("at", X1, X3)), value(variable(("at", X1, X3)), false)) :- action(action(("load-truck", X1, X2, X3))).
postcondition(action(("load-truck", X1, X2, X3)), effect(unconditional), variable(("in", X1, X2)),value(variable(("in", X1, X2)), true)) :- action(action(("load-truck", X1, X2, X3))).

action(action(("load-airplane", X1, X2, X3))) :- has(X1, type("package")), has(X2, type("airplane")), has(X3, type("location")).
precondition(action(("load-airplane", X1, X2, X3)), variable(("at", X1, X3)), value(variable(("at", X1, X3)), true)) :- action(action(("load-airplane", X1, X2, X3))).
precondition(action(("load-airplane", X1, X2, X3)), variable(("at", X2, X3)), value(variable(("at", X2, X3)), true)) :- action(action(("load-airplane", X1, X2, X3))).
precondition(action(("load-airplane", X1, X2, X3)), variable(("airport", X3)), value(variable(("airport", X3)), true)) :- action(action(("load-airplane", X1, X2, X3))).
postcondition(action(("load-airplane", X1, X2, X3)), effect(unconditional), variable(("at", X1, X3)), value(variable(("at", X1, X3)), false)) :- action(action(("load-airplane", X1, X2, X3))).
postcondition(action(("load-airplane", X1, X2, X3)), effect(unconditional), variable(("in", X1, X2)), value(variable(("in", X1, X2)), true)) :- action(action(("load-airplane", X1, X2, X3))).

action(action(("unload-truck", X1, X2, X3))) :- has(X1, type("package")), has(X2, type("truck")), has(X3, type("location")).
precondition(action(("unload-truck", X1, X2, X3)), variable(("at", X2, X3)), value(variable(("at", X2, X3)), true)) :- action(action(("unload-truck", X1, X2, X3))).
precondition(action(("unload-truck", X1, X2, X3)), variable(("in", X1, X2)), value(variable(("in", X1, X2)), true)) :- action(action(("unload-truck", X1, X2, X3))).
postcondition(action(("unload-truck", X1, X2, X3)), effect(unconditional), variable(("in", X1, X2)), value(variable(("in", X1, X2)), false)) :- action(action(("unload-truck", X1, X2, X3))).
postcondition(action(("unload-truck", X1, X2, X3)), effect(unconditional), variable(("at", X1, X3)), value(variable(("at", X1, X3)), true)) :- action(action(("unload-truck", X1, X2, X3))).

action(action(("unload-airplane", X1, X2, X3))) :- has(X1, type("package")), has(X2, type("airplane")), has(X3, type("location")).
precondition(action(("unload-airplane", X1, X2, X3)), variable(("in", X1, X2)), value(variable(("in", X1, X2)), true)) :- action(action(("unload-airplane", X1, X2, X3))).
precondition(action(("unload-airplane", X1, X2, X3)), variable(("at", X2, X3)), value(variable(("at", X2, X3)), true)) :- action(action(("unload-airplane", X1, X2, X3))).
precondition(action(("unload-airplane", X1, X2, X3)), variable(("airport", X3)), value(variable(("airport", X3)), true)) :- action(action(("unload-airplane", X1, X2, X3))).
postcondition(action(("unload-airplane", X1, X2, X3)), effect(unconditional), variable(("in", X1, X2)), value(variable(("in", X1, X2)), false)) :- action(action(("unload-airplane", X1, X2, X3))).
postcondition(action(("unload-airplane", X1, X2, X3)), effect(unconditional), variable(("at", X1, X3)), value(variable(("at", X1, X3)), true)) :- action(action(("unload-airplane", X1, X2, X3))).

action(action(("drive-truck", X1, X2, X3))) :- has(X1, type("truck")), has(X2, type("location")), has(X3, type("location")).
precondition(action(("drive-truck", X1, X2, X3)), variable(("at", X1, X2)), value(variable(("at", X1, X2)), true)) :- action(action(("drive-truck", X1, X2, X3))).
precondition(action(("drive-truck", X1, X2, X3)), variable(("road", X2, X3)), value(variable(("road", X2, X3)), true)) :- action(action(("drive-truck", X1, X2, X3))).
postcondition(action(("drive-truck", X1, X2, X3)), effect(unconditional), variable(("at", X1, X2)), value(variable(("at", X1, X2)), false)) :- action(action(("drive-truck", X1, X2, X3))).
postcondition(action(("drive-truck", X1, X2, X3)), effect(unconditional), variable(("at", X1, X3)), value(variable(("at", X1, X3)), true)) :- action(action(("drive-truck", X1, X2, X3))).

action(action(("fly-airplane", X1, X2, X3))) :- has(X1, type("airplane")), has(X2, type("location")), has(X3, type("location")).
precondition(action(("fly-airplane", X1, X2, X3)), variable(("at", X1, X2)), value(variable(("at", X1, X2)), true)) :- action(action(("fly-airplane", X1, X2, X3))).
precondition(action(("fly-airplane", X1, X2, X3)), variable(("airport", X2)), value(variable(("airport", X2)), true)) :- action(action(("fly-airplane", X1, X2, X3))).
precondition(action(("fly-airplane", X1, X2, X3)), variable(("airport", X3)), value(variable(("airport", X3)), true)) :- action(action(("fly-airplane", X1, X2, X3))).
postcondition(action(("fly-airplane", X1, X2, X3)), effect(unconditional), variable(("at", X1, X2)), value(variable(("at", X1, X2)), false)) :- action(action(("fly-airplane", X1, X2, X3))).
postcondition(action(("fly-airplane", X1, X2, X3)), effect(unconditional), variable(("at", X1, X3)), value(variable(("at", X1, X3)), true)) :- action(action(("fly-airplane", X1, X2, X3))).

%---------------------------------------
% problem
%---------------------------------------

% objects
constant(constant("package3")).
has(constant("package3"), type("package")).

constant(constant("package1")).
has(constant("package1"), type("package")).

constant(constant("truck1")).
has(constant("truck1"), type("truck")).

constant(constant("plane1")).
has(constant("plane1"), type("airplane")).

constant(constant("city6-1")).
has(constant("city6-1"), type("location")).

constant(constant("city1-1")).
has(constant("city1-1"), type("location")).

constant(constant("city6-2")).
has(constant("city6-2"), type("location")).

constant(constant("city4-2")).
has(constant("city4-2"), type("location")).

constant(constant("city1-2")).
has(constant("city1-2"), type("location")).

% initial state
initialState(variable(("at", constant("plane1"), constant("city1-1"))), value(variable(("at", constant("plane1"), constant("city1-1"))), true)).
initialState(variable(("at", constant("truck1"), constant("city1-1"))), value(variable(("at", constant("truck1"), constant("city1-1"))), true)).
initialState(variable(("at", constant("package3"), constant("city1-1"))), value(variable(("at", constant("package3"), constant("city1-1"))), true)).
initialState(variable(("at", constant("package1"), constant("city4-2"))), value(variable(("at", constant("package1"), constant("city4-2"))), true)).
initialState(variable(("airport", constant("city1-1"))), value(variable(("airport", constant("city1-1"))), true)).
initialState(variable(("airport", constant("city6-1"))), value(variable(("airport", constant("city6-1"))), true)).
%initialState(variable(("airport", constant("city4-2"))), value(variable(("airport", constant("city4-2"))), true)).
initialState(variable(("road", constant("city1-1"), constant("city1-2"))), value(variable(("road", constant("city1-1"), constant("city1-2"))), true)).
initialState(variable(("road", constant("city1-2"), constant("city4-2"))), value(variable(("road", constant("city1-2"), constant("city4-2"))), true)).
initialState(variable(("road", constant("city4-2"), constant("city6-2"))), value(variable(("road", constant("city4-2"), constant("city6-2"))), true)).
initialState(variable(("road", constant("city6-2"), constant("city6-1"))), value(variable(("road", constant("city6-2"), constant("city6-1"))), true)).

initialState(X, value(X, false)) :- variable(X), not initialState(X, value(X, true)).

% goal
goal(variable(("at", constant("package3"), constant("city6-1"))), value(variable(("at", constant("package3"), constant("city6-1"))), true)).
goal(variable(("at", constant("package1"), constant("city6-1"))), value(variable(("at", constant("package1"), constant("city6-1"))), true)).
