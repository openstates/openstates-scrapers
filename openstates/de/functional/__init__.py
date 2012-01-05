"""
This modules provides commonly-used tools for functional programming.

Other modules/functions that might be of interest for functional-paradigm
programmers:
    + the built-in functions `max`, `min`, `lambda`, `map` and `filter`
    + the `operator` module
    + the `itertools` module
"""

#################################################################
### The C version of partial originally by Hye-Shik Chang <perky@FreeBSD.org>
### with adaptations by Raymond Hettinger <python@rcn.com>
### translated into Python by Collin Winter <collinw@gmail.com>
###
### All other function definitions translated to Python by
### Collin Winter from the Haskell originals found in the
### Haskell 98 Report, edited by Simon Peyton-Jones <simonpj@microsoft.com>
###
### Copyright (c) 2004-2006 Python Software Foundation.
### All rights reserved.
#################################################################

### partial class
###
### This handles partial function application
#################################################################

class partial(object):
    """
    partial(func, *args, **keywords) - new function with partial application
        of the given arguments and keywords.
    """
    def __init__(self, func, *args, **kwargs):
        if not callable(func):
            raise TypeError("the first argument must be callable")

        self.func = func
        self.args = tuple(args)
        self.kwargs = dict(kwargs)
        self._dict = None

    def __call__(self, *args, **kwargs):
        applied_args = self.args + args

        applied_kwargs = dict(self.kwargs)
        applied_kwargs.update(kwargs)

        return self.func(*applied_args, **applied_kwargs)

    def _getdict(self):
        if self._dict is None:
            return dict()

    def _setdict(self, val):
        assert isinstance(val, dict)

        self._dict = val

    def _deldict(self):
        raise TypeError("a partial object's dictionary may not be deleted")

    __dict__ = property(_getdict, _setdict, _deldict)
    
### compose
#################################################################

def compose(func_1, func_2, unpack=False):
    """
    compose(func_1, func_2, unpack=False) -> function
    
    The function returned by compose is a composition of func_1 and func_2.
    That is, compose(func_1, func_2)(5) == func_1(func_2(5))
    """
    if not callable(func_1):
        raise TypeError("First argument to compose must be callable")
    if not callable(func_2):
        raise TypeError("Second argument to compose must be callable")
    
    if unpack:
        def composition(*args, **kwargs):
            return func_1(*func_2(*args, **kwargs))
    else:
        def composition(*args, **kwargs):
            return func_1(func_2(*args, **kwargs))
    return composition

### foldl
#################################################################
                        
def _foldl(func, base, itr):
    try:
        first = itr.next()
    except StopIteration:
        return base

    return _foldl(func, func(base, first), itr)

def foldl(func, start, itr):
    """
    foldl(function, start, iterable) -> object

    Takes a binary function, a starting value (usually some kind of 'zero'), and
    an iterable. The function is applied to the starting value and the first
    element of the list, then the result of that and the second element of the
    list, then the result of that and the third element of the list, and so on.
    
    foldl(add, 0, [1, 2, 3]) is equivalent to add(add(add(0, 1), 2), 3)
    """
    return _foldl(func, start, iter(itr))

### foldr
#################################################################

def _foldr(func, base, itr):
        try:
                first = itr.next()
        except StopIteration:
                return base
                
        return func(first, _foldr(func, base, itr))

def foldr(func, start, itr):
    """
    foldr(function, start, iterable) -> object
    
    Like foldl, but starts from the end of the iterable and works back toward the
    beginning. For example, foldr(subtract, 0, [1, 2, 3]) == 2, but
    foldl(subtract, 0, [1, 2, 3] == -6
    
    foldr(add, 0, [1, 2, 3]) is equivalent to add(1, add(2, add(3, 0)))
    """
    return _foldr(func, start, iter(itr))

### scanl
#################################################################

def _scanl(func, base, itr):
    """
    In Haskell:
    
    scanl        :: (a -> b -> a) -> a -> [a] -> [a]
    scanl f q xs =  q : (case xs of
                              [] -> []
                            x:xs -> scanl f (f q x) xs)
    """
    yield base
    
    for o in itr:
        base = func(base, o)
        yield base
    raise StopIteration

def scanl(func, start, itr):
    """
    scanl(func, start, iterable) -> iterator
    
    Like foldl, but produces a list of successively reduced values, starting
    from the left.
    scanr(f, 0, [1, 2, 3]) is equivalent to
    [0, f(0, 1), f(f(0, 1), 2), f(f(f(0, 1), 2), 3)]
    
    scanl returns a iterator over the result list. This is done so that the
    list may be calculated lazily.
    """
    if not callable(func):
        raise TypeError("First argument to scanl must be callable")
    itr = iter(itr)

    return _scanl(func, start, itr)

### scanr
#################################################################

def _scanr(func, q0, x_xs):
    """
    In Haskell:
    
    scanr             :: (a -> b -> b) -> b -> [a] -> [b]
    scanr f q0 []     =  [q0]
    scanr f q0 (x:xs) =  f x q : qs
                         where qs@(q:_) = scanr f q0 xs
    """
    
    try:
        # Handle the empty-list condition
        x = x_xs.next()
    except StopIteration:
        yield q0
        raise StopIteration

    qs = _scanr(func, q0, x_xs)

    q = qs.next()
    yield func(x, q)

    # this is the ": qs" from the Haskell definition
    yield q
    while True:
        yield qs.next()

def scanr(func, start, itr):
    """
    scanr(func, start, iterable) -> iterator
    
    Like foldr, but produces a list of successively reduced values, starting
    from the right.
    scanr(f, 0, [1, 2, 3]) is equivalent to
    [f(1, f(2, f(3, 0))), f(2, f(3, 0)), f(3, 0), 0]
    
    scanl returns a iterator over the result list. This is done so that the
    list may be calculated lazily.
    """
    if not callable(func):
        raise TypeError("First argument to scanr must be callable")
    itr = iter(itr)
    
    return _scanr(func, start, itr)

### flip
################################################################

try:
    reversed
except NameError:
    def reversed(seq):
        rev = list(seq)
        rev.reverse()
        return iter(rev)

def flip(func):
    """
    flip(func) -> function
    
    flip causes `func` to take its non-keyword arguments in reverse order. The
    returned function is a wrapper around `func` that makes this happen.
    """
    if not callable(func):
        raise TypeError("First argument to flip must be callable")
    
    def flipped_func(*args, **kwargs):
        return func(*reversed(args), **kwargs)
    return flipped_func

### id
################################################################

def id(obj):
    """
    id(obj) -> object
    
    The identity function. id(obj) returns obj unchanged.
    
    >>> obj = object()
    >>> id(obj) is obj
    True
    """
    return obj

### map
################################################################

def map(function, iterable):
    """
    map(function, iterable) -> list
    
    Applies function to each element of iterable, returning a list
    of the resulting values. Basically, this is like the builtin map
    function, except we only take a single iterable and there's none
    of that map(None, ...) nonsense.
    """

    return [function(x) for x in iterable]

### filter
################################################################
    
def filter(function, iterable):
    """
    filter(function, iterable) -> list
    
    Applies function to each element of iterable, returning a list
    of those elements where function returned True. Basically, this
    is like the builtin map, except that functional.filter() treats
    subclasses of str/tuple/unicode correctly, and that filter()'s
    return type is always list.
    """

    if function is bool:
        return [x for x in iterable if x]

    return [x for x in iterable if function(x)]
