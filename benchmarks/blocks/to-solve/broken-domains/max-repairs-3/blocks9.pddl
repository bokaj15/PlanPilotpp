(define (domain blocks)
  (:requirements :strips :typing)
  (:types block)
  (:predicates (on ?x - block ?y - block)
	           (ontable ?x - block)
	           (clear ?x - block)
	           (handempty)
	           (holding ?x - block)
  )

  (:action pick-up
	     :parameters (?x - block)
	     :precondition (and (clear ?x) (ontable ?x) (handempty)) 
	     :effect
	     (and 
	     	   (not (ontable ?x))
				   (not (clear ?x))
				   (not (handempty))
				   (holding ?x)
				   )
 )

  (:action put-down
	     :parameters (?x - block)
	     :precondition (and (holding ?x) (ontable ?x))
	     :effect
		     (and 
		       (not (holding ?x))
			   (clear ?x)
			   (handempty)
			   (ontable ?x)
			   )
	)

  (:action stack
	     :parameters (?x - block ?y - block)
	     :precondition (and (holding ?x) (clear ?y))
	     :effect
			     (and 
			     	(not (holding ?x))
				   (not (clear ?y))
				   (clear ?x)
				   (on ?x ?y)
				   )
)

  (:action unstack
	     :parameters (?x - block ?y - block)
	     :precondition (and (on ?x ?y) (clear ?x) (handempty) (holding ?x))
	     :effect
			     (and 
				   (clear ?y)
				   (holding ?x)
				   (not (clear ?x))
				   (not (handempty))
				   (not (on ?x ?y))
				   )
	)

)
