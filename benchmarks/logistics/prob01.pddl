(define (problem strips-log-x-1)
  (:domain logistics-strips)
  (:objects
    package3 package1 - package
    truck1 - truck
    plane1 - airplane
    city6-1 city1-1 city6-2 city4-2 city1-2 - location
)
    
  (:init
    (at plane1 city1-1)
    (at truck1 city1-1)
    (at package3 city1-1)
    (at package1 city4-2)

    (airport city1-1)
    (airport city6-1)
    (airport city4-2)

    (road city1-1 city1-2)
    (road city1-2 city4-2)
    (road city4-2 city6-2)
    (road city6-2 city6-1)
    )

  (:goal (and
           (at package3 city6-1)
           (at package1 city6-1)
          )
  )
)

; + occurs(action(("unload-truck",constant("package3"),constant("truck1"),constant("city6-1"))),8)