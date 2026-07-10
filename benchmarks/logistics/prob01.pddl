(define (problem strips-log-x-1)
  (:domain logistics-strips)
  (:objects
    package2 package1 - package
    truck1 - truck
    plane1 - airplane
    city-1 city-2 city-3 city-4 city-5 city-6 - location
)
    
  (:init
    (at plane1 city-2)
    (at truck1 city-1)
    (at package1 city-1)
    (at package2 city-2)

    (airport-in city-2)
    (airport-in city-6)

    (road city-1 city-2)
    (road city-2 city-3)
    (road city-3 city-4)
    (road city-4 city-5)
    (road city-5 city-6)
    )

  (:goal (and
           (at package2 city-6)
           (at package1 city-6)
          )
  )
)

; + occurs(action(("unload-truck",constant("package3"),constant("truck1"),constant("city1"))),8)
; (action(("drive-truck",constant("truck1"),constant("city-1"),constant("city-2"))),5)


; unsolvable
; + occurs_sometime(action(("drive-truck",constant("truck1"),constant("city-2"),constant("city-3"))))
; + occurs_sometime(action(("fly-airplane",constant("plane1"),constant("city-2"),constant("city-6"))))
; + occurs_sometime(action(("unload-airplane",constant("package2"),constant("plane1"),constant("city-6"))))