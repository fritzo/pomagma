import functools


def for_each(examples):

    def decorator(fun):

        def fun_one(i):
            fun(examples[i])

        @functools.wraps(fun)
        def decorated():
            for i in xrange(len(examples)):
                yield fun_one, i

        return decorated
    return decorator


def for_each_kwargs(examples):

    def decorator(fun):

        def fun_one(i):
            fun(**examples[i])

        @functools.wraps(fun)
        def decorated():
            for i in xrange(len(examples)):
                yield fun_one, i

        return decorated
    return decorator


def for_each_context(get_context, examples):

    def decorator(fun):
        state = {}

        def fun_one(i):
            fun(state['context'], examples[i])

        @functools.wraps(fun)
        def decorated():
            with get_context() as context:
                state['context'] = context
                for i in xrange(len(examples)):
                    yield fun_one, i
            del state['context']

        return decorated
    return decorator
