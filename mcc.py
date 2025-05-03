#!/usr/bin/env python3
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Any
import os, sys

IOTA_COUNTER: int = 0
def iota(idx: int | None = None) -> int:
    global IOTA_COUNTER
    if isinstance(idx, int):
        IOTA_COUNTER = idx
    result: int = IOTA_COUNTER
    IOTA_COUNTER += 1
    return result

def default(cls: Any) -> Any:
    return field(default_factory=cls)

@dataclass
class TokenKind:
    UNDEFINED:  int = iota(256)
    EOF:        int = iota()
    IDENTIFIER: int = iota()
    NUMBER:     int = iota()

@dataclass
class Token:
    kind:  int = TokenKind.UNDEFINED
    begin: int = 0
    end:   int = 0

@dataclass
class Line:
    line_number: int         = 1
    line_offset: int         = 0
    tokens:      list[Token] = default(list)

@dataclass
class OS:
    UNDEFINED: int = iota(0)
    LINUX: int = iota()
    WINDOWS: int = iota()

@dataclass
class Entry:
    name:    str = "main"
    os:      int = OS.LINUX
    machine: str = "x86_64"

@dataclass
class Types:
    UNDEFINED: int = iota(0)
    VOID: int = iota()
    I8: int = iota()
    I16: int = iota()
    I32: int = iota()
    I64: int = iota()
    U8: int = iota()
    U16: int = iota()
    U32: int = iota()
    U64: int = iota()

@dataclass
class Value:
    _type: int        = Types.I64
    value: Any | None = None

@dataclass
class Parameter:
    name:  str   = "a"
    value: Value = default(Value)

@dataclass
class Block:
    statements:  list[Statement]  = default(list)
    expressions: list[Expression] = default(list)

@dataclass
class Func:
    name:        str             = "main"
    params:      list[Parameter] = default(list)
    return_type: int             = Types.VOID
    block:       Block           = default(Block)

@dataclass
class Program:
    entries: list[Entry] = default(list)
    funcs:   list[FuncDef]  = default(list)

class Lexer:
    def __init__(self, path: str) -> None:
        self.path:        str = path
        self.text:        str = ""
        self.index:       int = 0
        self.line_offset: int = 0
        self.lines:       int = 1

        try:
            with open(self.path, "rb") as file:
                self.text = file.read().decode()
        except FileNotFoundError:
            assert False, f"ERROR:Lexer({self.path}): Could not open file, please provide a valid file path!"

    def range(self, idx: int) -> bool:
        return idx < len(self.text)

    def has(self, s: str) -> bool:
        return all([self.range(self.index+i) and s[i]==self.text[self.index+i] for i in range(len(s))])

    def white(self, idx: str) -> bool:
        c: str = self.text[idx]
        return c==' ' or c=='\n' or c=='\r' or c=='\t'

    def linecomment(self, idx: int) -> bool:
        c: str = self.text[idx]
        d: str = self.text[idx+1]
        return c=='/' and d=='/'
    
    def blockcommentbegin(self, idx: int) -> bool:
        c: str = self.text[idx]
        d: str = self.text[idx+1]
        return c=='/' and d=='*'
    
    def blockcommentend(self, idx: int) -> bool:
        c: str = self.text[idx]
        d: str = self.text[idx+1]
        return c=='*' and d=='/'

    def digit(self, idx: int) -> bool:
        c: int = ord(self.text[idx])
        return c>=ord('0') and c<=ord('9')

    def identifier(self, idx: int) -> bool:
        c: int = ord(self.text[idx])
        return self.digit(idx) or c==ord('_') or (c>=ord('A') and c<=ord('Z')) or (c>=ord('a') and c<=ord('z'))

    def tokenise(self) -> Token:
        # skip whitespaces and comments
        run: bool = True
        while run and self.range(self.index):
            if self.white(self.index):
                # whitespaces: ` `, `\n`, `\r` and `\t`
                if self.text[self.index] == '\n':
                    self.lines += 1
                    self.line_offset = self.index + 1
                self.index += 1
            elif self.linecomment(self.index):
                # linecomment: `//`
                while self.range(self.index+1) and self.text[self.index] != '\n':
                    self.index += 1
            elif self.blockcommentbegin(self.index):
                # blockcomment: `/*` and `*/`
                # skip start of block comment `/*` to not get `/*/` as a valid block comment
                self.index += 2
                while self.range(self.index+1) and not self.blockcommentend(self.index):
                    if self.text[self.index] == '\n':
                        self.lines += 1
                        self.line_offset = self.index + 1
                    self.index += 1
                # skip end of block comment to not get `*/` as tokens!
                self.index += 2
            else:
                # no whitespace and comment found (break out of loop)
                run = False

        # return early if end of file is reached
        if not self.range(self.index):
            return Token(TokenKind.EOF, self.index, self.index)
        
        begin: int = self.index
        kind: int = TokenKind.UNDEFINED
        if self.has('+'):
            kind = ord('+')
        elif self.has(';'):
            kind = ord(';')
        elif self.has('@'):
            kind = ord('@')
        elif self.has('('):
            kind = ord('(')
        elif self.has(')'):
            kind = ord(')')
        elif self.has('{'):
            kind = ord('{')
        elif self.has('}'):
            kind = ord('}')
        else:
            while self.range(self.index) and self.digit(self.index):
                self.index += 1
            if begin != self.index:
                return Token(TokenKind.NUMBER, begin, self.index)
            
            while self.range(self.index) and self.identifier(self.index):
                self.index += 1
            if begin != self.index:
                return Token(TokenKind.IDENTIFIER, begin, self.index)

            c: int = ord(self.text[self.index])
            assert False, ("ERROR:Lexer(%i:%i:%s): Encountered an invalid token 0x%.4X" % (
                    self.line, self.line_offset-self.index, self.path)
                ) + f"{f' `{self.text[self.index]}`' if c>=0x20 and c<=0x7E else ''}!"

        self.index += 1
        return Token(kind, begin, self.index)
    
    def lex(self) -> list[Line]:
        l: int = self.lines
        lo: int = self.line_offset
        tokens: list[Token] = []
        token: Token = self.tokenise()
        lines: list[Line] = []
        
        while token.kind != TokenKind.EOF:
            if self.lines != l and len(tokens) >= 1:
                lines.append(Line(l, lo, tokens))
                tokens = []
                l = self.lines
                lo = self.line_offset
            tokens.append(token)
            token = self.tokenise()
        
        if len(tokens) >= 1:
            lines.append(Line(l, lo, tokens))

        return lines

class Parser:
    def __init__(self, lexer: Lexer) -> None:
        self.lexer: Lexer = lexer
        self.lines: list[Line] = self.lexer.lex()

    def expression(self) -> Expression:
        ...

    def type_expr(self) -> TypeExpr:
        ...

    def value_expr(self) -> ValueExpr:
        ...

    def block_stmt(self) -> Block:
        ...

    def func_expr(self) -> FuncDefExpr:
        ...

    def parse(self) -> Program:
        ...

def main() -> None:
    lexer: Lexer = Lexer("examples/test.mcs")
    
    lines: list[Line] = lexer.lex()
    for l in lines:
        for t in l.tokens:
            s: str = lexer.text[t.begin:t.end]
            print(f"{l.line_number}:{t.begin-l.line_offset}-{t.end-l.line_offset}:{t}{f' `{s}`'if len(s)==1 and ord(s)>=0x20 and ord(s)<=0x7E else f' `{s}`' if t.kind in (TokenKind.NUMBER, TokenKind.IDENTIFIER) else ''}!")

if __name__ == "__main__":
    main()
