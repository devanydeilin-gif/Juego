def get_level_config(level):
	# Cada nivel aumenta la velocidad y la cantidad de obstáculos
	base_spawn_rate = 60
	base_obstacle_speed = 3
	base_obstacles_to_pass = 10
	spawn_rate = max(20, base_spawn_rate - level * 4)
	obstacle_speed = base_obstacle_speed + level
	obstacles_to_pass = base_obstacles_to_pass + level * 5
	return {
		'spawn_rate': spawn_rate,
		'obstacle_speed': obstacle_speed,
		'obstacles_to_pass': obstacles_to_pass
	}
