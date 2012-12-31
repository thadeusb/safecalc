"""
Copyright (c) 2012 by Thadeus Burgess.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Based on code snippets released into the "public domain" from
http://effbot.org/zone/simple-top-down-parsing.htm
"""

import operator
import tokenize

from cStringIO import StringIO


class SymbolBase(object):
    sym_id = None
    lbp = 0
    value = None
    first = None
    second = None

    def eval(self, *args):
        op = self.parser.operator_map[self.sym_id]
        if isinstance(op, tuple):
            if self.second is not None:
                op = op[0]
            else:
                op = op[1]

        args = [x.eval(x) for x in (self.first, self.second) if x is not None]

        return op(*args)

    def nud(self):
        """
        Null denotation function. Token at beginning of language construct
        """
        raise SyntaxError()

    def led(self, left):
        """
        Left denotation function. Token appears inside the construct to the left
        """
        raise SyntaxError()

    def __repr__(self):
        if self.value:
            return "[%s %s]" % (self.sym_id, self.value)
        else:
            return "[%s %s %s]" % (self.sym_id, self.first, self.second)


class TopDownParser(object):
    def __init__(self, operator_map, sym_map):
        self.table = {}
        self.operator_map = {}
        self.operator_map.update(operator_map)
        self.token = None

        symbol = self.symbol

        symbol('(name)').nud = lambda self: self
        symbol('(literal)').nud = lambda self: self
        symbol('(end)')

        @self.method(symbol('(literal)'))
        def eval(symbol, *args):
            try:
                return int(symbol.value)
            except:
                try:
                    return float(symbol.value)
                except:
                    return symbol.value

        for sym_id, func in sym_map.items():
            symbol(sym_id).eval = func

    def tokenize_python(self, program):
        type_map = {
            tokenize.NUMBER: "(literal)",
            tokenize.STRING: "(literal)",
            tokenize.OP: "(operator)",
            tokenize.NAME: "(name)"
        }
        for t in tokenize.generate_tokens(StringIO(program).next):
            try:
                yield type_map[t[0]], t[1]
            except KeyError:
                if t[0] == tokenize.NL:
                    continue
                if t[0] == tokenize.ENDMARKER:
                    break
                else:
                    raise SyntaxError("SyntaxError")
        yield "(end)", "(end)"

    def tokenize(self, program):
        source = self.tokenize_python(program)

        for sym_id, value in source:
            if sym_id == "(literal)":
                symbol = self.table[sym_id]
                s = symbol()
                s.value = value
            else:
                symbol = self.table.get(value)
                if symbol:
                    s = symbol()
                elif sym_id == "(name)":
                    symbol = self.table[sym_id]
                    s = symbol()
                    s.value = value
                else:
                    raise SyntaxError("Unknown Operator (%r) = %s" % (sym_id, value))
            yield s

    def expression(self, rbp=0):
        t = self.token
        self.token = self.next()
        left = t.nud()
        while rbp < self.token.lbp:
            t = self.token
            self.token = self.next()
            left = t.led(left)
        return left

    def parse(self, program):
        self.next = self.tokenize(program).next
        self.token = self.next()
        return self.expression()

    def symbol(self, sym_id, bp=0):
        try:
            s = self.table[sym_id]
        except KeyError:
            class s(SymbolBase):
                pass
            s.__name__ = 'Symbol-' + sym_id
            s.sym_id = sym_id
            s.value = None
            s.lbp = bp
            s.parser = self

            self.table[sym_id] = s

        s.lbp = max(bp, s.lbp)

        return s

    def infix(self, sym_id, bp=0):
        def led(self, left):
            self.first = left
            self.second = self.parser.expression(bp)
            return self
        self.symbol(sym_id, bp).led = led

    def infix_r(self, sym_id, bp=0):
        def led(self, left):
            self.first = left
            self.second = self.parser.expression(bp-1)
            return self
        self.symbol(sym_id, bp).led = led

    def prefix(self, sym_id, bp=0):
        def nud(self):
            self.first = self.parser.expression(bp)
            return self
        self.symbol(sym_id, bp).nud = nud

    def advance(self, sym_id):
        if sym_id and self.token.sym_id != sym_id:
            raise SyntaxError("Expected %r, got %r" % (sym_id, self.token.sym_id))
        self.token = self.next()

    def method(self, s):
        def bind(fn):
            setattr(s, fn.__name__, fn)
        return bind


class CtxCalculator(TopDownParser):
    def __init__(self, ctx=None):
        if ctx is None:
            ctx = {}
        self.ctx = ctx

        super(CtxCalculator, self).__init__(
            operator_map = {
                '+': (operator.add, operator.pos),
                '-': (operator.sub, operator.neg),
                '/': operator.div,
                '//': operator.floordiv,
                '*': operator.mul,
                '**': operator.pow,
                '%': operator.mod,
                '[': self.operator_lookup_name,
            },
            sym_map = {
                '(name)': self.lookup_name
            },
        )

        s = self.symbol
        i = self.infix
        ir = self.infix_r
        p = self.prefix

        i('<<', 100)
        i('>>', 100)

        i('+', 110)
        i('-', 110)
        i('*', 120)
        i('/', 120)
        i('//', 120)
        i('%', 120)

        p('-', 130)
        p('+', 130)

        ir('**', 140)

        s('.', 150)
        s('[', 150)
        s('(', 150)

        s(')')
        s(']')

        @self.method(s('('))
        def nud(symbol):
            expr = symbol.parser.expression()
            symbol.parser.advance(')')
            return expr

        @self.method(s('.'))
        def led(symbol, left):
            if symbol.parser.token.sym_id != "(name)":
                raise SyntaxError("Expected an attribute name.")

            symbol.first = left
            symbol.second = symbol.parser.token
            symbol.parser.advance()
            return symbol

        @self.method(s('['))
        def led(symbol, left):
            symbol.first = left
            symbol.second = symbol.parser.expression()
            symbol.parser.advance(']')
            return symbol

    def lookup_name(self, symbol):
        if symbol.value in self.ctx_extras:
            return self.ctx_extras[symbol.value]
        return self.ctx[symbol.value]

    def operator_lookup_name(self, sub_ctx, key):
        key = key.strip().strip('"\'')
        return sub_ctx[key]

    def parse(self, program, **ctx_extras):
        self.ctx_extras = ctx_extras
        return super(CtxCalculator, self).parse(program)
        
    def eval(self, program, **ctx_extras):
        parser = self.parse(program, **ctx_extras)
        return parser.eval(parser)


if __name__ == '__main__':
    parser = CtxCalculator({'value': 1})

    def test(expr, ctx={}):
        x = parser.parse(expr, **ctx)
        ans = x.eval(x)
        print expr, x, '=', ans
        return ans

    test('112')
    test('1+2')
    test('1.3+2')
    test('1+2/2')
    test('-1')
    test('value+1')
    test('value')

    ctx = {'value': 2.0}
    test('value+1', ctx)

    ctx = {'a': 5,
           'b': 2}

    c2 = test('a**2 * b**2', ctx)

    test('((5+5)*2/(3+(2*1)+1*2) )+ 5')

