# For Developers

## Dataflow Architecture

![Architecture](architecture.png)

### State

- Languages - finite generating grammars of combinatory algebras
- Theory - finite relational theories of combinatory algebras
- Atlas - an algebraic knowledge bases of relations in each algebra

### Actors

- Compiler - creates core theory and surveying strategies
- Surveyors - explore a region of a combinatory algebra via forward chaining
- Cartographers - direct surveyors and incorporate surveys into the atlas
- Linguist - fits languages to analyst workload and proposes new basic terms
- Language Reviewer - ensures new language modifications are safe
- Theorist - makes conjectures and tries to prove them using various strategies
- Theory Reviewer - suggests new inference stragies to address open conjectures
- Analyst - performs deeper static analysis to support clients

### Workflows

- Compile: interpret theory to create core facts and inference strategies
- Explore: expand atlas by surveying and inferring global facts
- Analyze: provide static analysis server to analyst clients
- Evolve Language: tune grammar weights based on analyst; propose new words
- Recover (after Fregean collapse): assess damage; pinpoint problem; rebuild
