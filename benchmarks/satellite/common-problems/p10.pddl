;./satgen 3 4 1 2 2 4

(define (problem strips-sat-x-1)
(:domain satellite)
(:objects
	satellite0 - satellite
	instrument0 - instrument
	satellite1 - satellite
	instrument1 - instrument
	satellite2 - satellite
	instrument2 - instrument
	satellite3 - satellite
	instrument3 - instrument
	spectrograph0 - mode
	infrared1 - mode
	Star1 - direction
	Star0 - direction
	Star2 - direction
	Phenomenon3 - direction
	Star4 - direction
	Star5 - direction
)
(:init
	(supports instrument0 infrared1)
	(supports instrument0 spectrograph0)
	(calibration_target instrument0 Star0)
	(on_board instrument0 satellite0)
	(power_avail satellite0)
	(pointing satellite0 Star4)
	(supports instrument1 infrared1)
	(supports instrument1 spectrograph0)
	(calibration_target instrument1 Star0)
	(on_board instrument1 satellite1)
	(power_avail satellite1)
	(pointing satellite1 Star2)
	(supports instrument2 spectrograph0)
	(supports instrument2 infrared1)
	(calibration_target instrument2 Star0)
	(on_board instrument2 satellite2)
	(power_avail satellite2)
	(pointing satellite2 Star2)
	(supports instrument3 infrared1)
	(supports instrument3 spectrograph0)
	(calibration_target instrument3 Star0)
	(on_board instrument3 satellite3)
	(power_avail satellite3)
	(pointing satellite3 Star4)
)
(:goal (and
	(pointing satellite0 Star0)
	(pointing satellite1 Star4)
	(pointing satellite3 Star5)
	(have_image Star2 spectrograph0)
	(have_image Phenomenon3 spectrograph0)
	(have_image Star4 infrared1)
	(have_image Star5 spectrograph0)
))

)
