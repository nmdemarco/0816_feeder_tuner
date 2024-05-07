This project helps you tune 0816-style pick and place component feeders.
These feeders are 3D printed, and use hobby servos to advance components precisely. The precision and accuracy varies from feeder to feeder. The command set for these feeders usually includes an M620 code to configure the feeder positions. This project helps you configure the positions.

The project includes two major classes:

Feeder - these are the individual feeders themselves. Unfortunately, they have no onboard memory, so they cannot store their own tuning parameters.

FeederControl - these are the connection points, often called 'slots', where feeders can be connected. The feeder controller can store the precise tuning parameters required by a specific feeder.

To use this tool:
1. label each feeder with an id.
1. Attach feeders to slots.
1. Start working with a single slot and a single feeder.
1. Relate the feeder to the slot so the tuner knows which feeder an slot to tune.
1. Start tuning using the tuning controls.
1. When done, save the new tuning parameters.

Running feeders
Once all feeders have been tuned, you can move feeders to different slots, and the tuning parmeters will be updated accoordingly.

##Protocol for PandaPlacer BambooFeeder Controller

Taken from https://docs.mgrl.de/maschine:pickandplace:feeder:0816feeder:mcodes

Additonal M codes:
M621 ; return configuration for all boards and positions.
M621 Bx ; return configuration for position x (e.g board 1, position 5 is 105)

