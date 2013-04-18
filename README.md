# Pomagma

Adventures in Abstractland.

## System Architecture

![Architecture](doc/architecture.png)

### State

- Law - regulations for roadways in Abstractland
- Vehicles - various means of navigating Abstractland
- Atlas - charts of the known extents of Abstractland
- History - a record of past adventures in Abstractland

### Actors

- City Planner - decides city extents and creates surveying strategies
- Surveyors - explore and measures uncharted territory
- Cartographers - direct surveyors and incorporate surveys into the atlas
- Adventurers - wander the world, driven by curiosity and a penchant for pattern
- Guides - guide adventurers through Abstractland
- Tour Agency - coordinates guides, dispatches information, records routes
- Engineers - develop vehicles for various terrain
- Safety Board - ensure new vehicles will be safe for future traffic patterns
- Economists - propose new routes between common destinations
- Transportation Committee - evaluates transportation bills

### Workflows

- Plan: interpret law to decide city extents and create surveying strategies
- Survey: select a region; survey it; aggregate measurements into atlas
- Adventure: travel around Abstractland with a guide
- Engineer: optimize vehicles based on driving history
- Invent: invent new parts for vehicles; review for safety
- Legislate: propose new routes; evaluate economic effects; legislate
- Recover (after Fregean collapse): assess damage; pinpoint problem; rebuild

## Milestones

- Viable - prove concept in prototype [DONE](http://github.com/fritzo/Johann)
- Parallel - run surveyor system tests (h4, sk, skj) DONE
- Scalable - implement cartographer DONE
- Distributed - run survey workflow on ec2
- Interactive - implement guide as web-app
- Cumulative - record adventures in history
- Efficient - tune vehicle based on routes
- Innovative - propose new vehicle components based on routes
- Economical - propose new routes between common destinations
- Reflective - locate actors within Abstractland

## License

Copyright (C) 2005-2013 Fritz Obermeyer<br/>
Licensed under the MIT license:<br/>
http://www.opensource.org/licenses/mit-license.php
