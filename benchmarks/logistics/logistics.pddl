(define (domain logistics-strips)
  (:requirements :strips :typing)

  (:types
    location locatable - object
    package vehicle - locatable
    truck airplane - vehicle
    airport city - location
    )

  (:predicates
    (at ?obj - locatable ?loc - location)
    (in ?obj - package ?veh - vehicle)
    (road ?loc-from - location ?loc-to - location)
    (airport ?loc - location)
  )
; enabled(add_effect("load-truck",("in",par1,par2),true))

  (:action LOAD-TRUCK
    :parameters (?obj - package ?truck - truck ?loc - location)
    :precondition (and (at ?truck ?loc) 
                       (at ?obj ?loc)
                  )
    :effect (and (not (at ?obj ?loc)) 
                 (in ?obj ?truck)
            )
  )

  (:action LOAD-AIRPLANE
    :parameters (?obj - package ?airplane - airplane ?loc - location)
    :precondition (and (at ?obj ?loc) 
                       (at ?airplane ?loc)
                       (airport ?loc)
                  )
    :effect (and (not (at ?obj ?loc)) 
                 (in ?obj ?airplane)
            )
  )

  (:action UNLOAD-TRUCK
    :parameters (?obj - package ?truck - truck ?loc - location)
    :precondition (and (at ?truck ?loc) 
                       (in ?obj ?truck)
                  )
    :effect (and (not (in ?obj ?truck)) 
                 (at ?obj ?loc)
            )
  )

  (:action UNLOAD-AIRPLANE
    :parameters (?obj - package ?airplane - airplane ?loc - location)
    :precondition (and (in ?obj ?airplane) 
                       (at ?airplane ?loc)
                       (airport ?loc)
                  )
    :effect (and (not (in ?obj ?airplane)) 
                 (at ?obj ?loc)
            )
  )

  (:action DRIVE-TRUCK
    :parameters (?truck - truck ?loc-from ?loc-to - location)
    :precondition (and (at ?truck ?loc-from) 
                       (road ?loc-from ?loc-to)
                  )
    :effect (and (not (at ?truck ?loc-from)) 
                 (at ?truck ?loc-to)
            )
  )


  (:action FLY-AIRPLANE
    :parameters (?airplane - airplane ?loc-from ?loc-to - location)
    :precondition (and (at ?airplane ?loc-from)
                       (airport ?loc-from)
                       (airport ?loc-to)
        )
    :effect (and (not (at ?airplane ?loc-from)) 
                 (at ?airplane ?loc-to)
            )
  )
)