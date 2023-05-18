TEST_TABLE = [
	[
		# test name
		"basic_test",

		# known actions
		["moveTo", "interact"],

		# input
		"OK, so, first you need to go to the stove. Then you need to interact with it. Then go to the onions and interact with those.",

		# want decomp
		[
			("go", ["stove"]),
			("interact", ["stove"]),
			("go", ["onions"]),
			("interact", ["onions"]),
		],

		# want mapped
		[
			("known", "MOVETO", ["stove"]),
			("known", "INTERACT", ["stove"]),
			("known", "MOVETO", ["onions"]),
			("known", "INTERACT", ["onions"]),
		],
	],

	[
		# test name
		"uh_and_yeah",

		# known actions
		["moveTo", "interact"],

		# input
		"Move to the onions and then move to the stove. Interact, uh, with the stove. Yeah. Then go back to the onions.",

		# want decomp
		[
			("move", ["onions"]),
			("move", ["stove"]),
			("interact", ["stove"]),
			("go", ["onions"]),
		],

		# want mapped
		[
			("known", "MOVETO", ["onions"]),
			("known", "MOVETO", ["stove"]),
			("known", "INTERACT", ["stove"]),
			("known", "MOVETO", ["onions"]),
		],
	],

	[
		# test name
		"run_back_means_moveTo",

		# known actions
		["moveTo", "interact"],

		# input
		"Head to the onions. Move to the stove. Interact, uh, with the stove. Yeah. Then run back to the onions.",

		# want decomp
		[
			("head", ["onions"]),
			("move", ["stove"]),
			("interact", ["stove"]),
			("run", ["onions"]),
		],

		# want mapped
		[
			("known", "MOVETO", ["onions"]),
			("known", "MOVETO", ["stove"]),
			("known", "INTERACT", ["stove"]),
			("known", "MOVETO", ["onions"]),
		],
	],

	[
		# test name
		"unknown_action_alone",

		# known actions
		["moveTo", "interact"],

		# input
		# "Please go to the stove and make an onion soup.",
		"Please make an onion soup.",

		# want decomp
		[
			# ("go", ["stove"]),
			("make", ["onion soup"]),
		],

		# want mapped
		[
			# ("known", "MOVETO", ["stove"]),
			("unknown", "make", ["onion soup"]),
		],
	],

	[
		# test name
		"mixed_unknown_known",

		# known actions
		["moveTo", "interact"],

		# input
		"Please go to the stove and make an onion soup.",

		# want decomp
		[
			("go", ["stove"]),
			("make", ["onion soup"]),
		],

		# want mapped
		[
			("known", "MOVETO", ["stove"]),
			("unknown", "make", ["onion soup"]),
		],
	],
]
