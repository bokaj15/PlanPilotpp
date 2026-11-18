

(define (problem BW-rand-6)
(:domain blocks)
(:objects b1 b2 b3 b4 b5 b6 - block)
(:init
(handempty)
(on b1 b2)
(on b2 b5)
(ontable b3)
(on b4 b6)
(on b5 b3)
(on b6 b1)
(clear b4)
)
(:goal
(and
(on b1 b2)
(on b2 b5)
(on b5 b6)
(on b6 b3))
)
)


