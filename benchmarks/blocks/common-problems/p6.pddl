

(define (problem BW-rand-5)
(:domain blocks)
(:objects b1 b2 b3 b4 b5 - block)
(:init
(handempty)
(on b1 b4)
(ontable b2)
(on b3 b2)
(on b4 b3)
(on b5 b1)
(clear b5)
)
(:goal
(and
(on b1 b3)
(on b2 b1)
(on b5 b4))
)
)


