# Workflow Management

## Example

    # on master node
    python -m pomagma.workflow.decider start &
    python -m pomagma.workflow.reporter start &

    # on atlas node
    python -m pomagma.workflow.grow start-trimmer &
    python -m pomagma.workflow.grow start-aggregator sk &
    python -m pomagma.workflow.grow start-aggregator skj &

    # on grower node 1
    python -m pomagma.workflow.grow start-grower sk 16383 &

    ...

    # on grower node N
    python -m pomagma.workflow.grow start-grower skj 32767 &

    # TODO make these adaemon processes
