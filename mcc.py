#!/usr/bin/env python3
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, override
from copy import deepcopy
import sys, subprocess

DEBUG: bool = True

IOTA_COUNTER: int = 0
def iota(index: int | None = None) -> int:
    global IOTA_COUNTER
    if isinstance(index, int):
        IOTA_COUNTER = index
    result: int = IOTA_COUNTER
    IOTA_COUNTER += 1
    return result

def default(cls: Any) -> Any:
    return field(default_factory=cls)

def get_kind(cls: Any, kind: Any) -> str:
    d: dict[str, int] = asdict(cls())
    return [k for k in d if kind==d[k]][0]

def cmd(*args) -> str:
    return subprocess.run(*args, capture_output=True).stdout

@dataclass
class TokenKind:
    undefined:   int = iota(0)
    eof:         int = iota()
    identifier:  int = iota()
    function:    int = iota()
    _return:     int = iota()
    integer:     int = iota()
    string:      int = iota()
    at:          int = iota()
    dotdotdot:   int = iota()
    comma:       int = iota()
    colon:       int = iota()
    semi_colon:  int = iota()
    open_paren:  int = iota()
    close_paren: int = iota()
    open_brace:  int = iota()
    close_brace: int = iota()
    count:       int = iota()

@dataclass
class Token:
    kind:   int = TokenKind.undefined
    begin:  int = 0
    end:    int = 0
    line:   int = 1
    offset: int = 0

@dataclass
class Directives:
    undefined: int = iota(0)
    extern:    int = iota()
    entry:     int = iota()
    count:     int = iota()

@dataclass
class Type:
    undefined: int = iota(0)
    u8:        int = iota()
    u16:       int = iota()
    u32:       int = iota()
    u64:       int = iota()
    usize:     int = iota()
    i8:        int = iota()
    i16:       int = iota()
    i32:       int = iota()
    i64:       int = iota()
    pointer:   int = iota()
    array:     int = iota()
    string:    int = iota()
    count:     int = iota()

@dataclass
class ExprKind:
    undefined: int = iota(0)
    block:     int = iota()
    count:     int = iota()

@dataclass
class Expression:
    kind: int        = ExprKind.undefined
    expr: Any | None = None

@dataclass
class BlockExpr:
    exprs: list[Expression] = default([])

@dataclass
class ArgumentExpr:
    _type: int        = Type.undefined
    value: Any | None = None

@dataclass
class FuncDefExpr:
    args: list[ArgumentExpr] = default([])
    body: BlockExpr          = default(BlockExpr)

@dataclass
class StmtKind:
    undefined: int = iota(0)
    _return:   int = iota()
    count:     int = iota()

@dataclass
class ExprStmt:
    kind: int        = StmtKind.undefined
    stmt: Any | None = None

@dataclass
class ReturnStmt:
    _type: int = Type.undefined
    expr:  Expression = default(Expression)

@dataclass
class Program:
    externs:   list[FuncDefExpr] = default(list)
    functions: list[FuncDefExpr] = default(list)
    entry:     list[FuncDefExpr] = default(list)

class Logger:
    def print(self, msg: str, end: str = '\n') -> None:
        sys.stderr.write(msg + end)

    def error(self, msg: str, sep: str = " ", _exit: bool = True) -> None:
        self.print(f"ERROR:{sep}{msg}")
        if _exit:
            sys.exit(1)

    def warning(self, msg: str, sep: str = " ") -> None:
        self.print(f"WARNING:{sep}{msg}")

    def info(self, msg: str, sep: str = " ") -> None:
        self.print(f"INFO:{sep}{msg}")

    def panic(self, msg: str) -> None:
        if DEBUG:
            self.print(f"PANIC:{sys._getframe().f_back.f_lineno}:{sys.argv[0]}: {msg}")
            sys.exit(1)

    def todo(self, msg: str) -> None:
        if DEBUG:
            self.print(f"TODO:{sys._getframe().f_back.f_lineno}:{sys.argv[0]}: {msg}")
            sys.exit(1)

    def unimplemented(self, msg: str) -> None:
        if DEBUG:
            self.print(f"UNIMPLEMENTED:{sys._getframe().f_back.f_lineno}:{sys.argv[0]}: {msg}")
            sys.exit(1)

log: Logger = Logger()

class Lexer(Logger):
    def __init__(self, path: str) -> None:
        self.path:      str        = path
        self.text:      str        = ""
        self.cursor:    int        = -2     # set to -2 so after populating curr_char and next_char it points at 0
        self.offset:    int        = 0
        self.line:      int        = 1
        self.curr_char: str | None = None
        self.next_char: str | None = None

        try:
            with open(self.path, "r") as file:
                self.text = file.read()
        except FileNotFoundError:
            self.error(f"While lexing could not open file `{self.path}`, please provide a valid file path!", False)

        # populate curr_char and next_char
        self.advance(2)

    def error(self, msg: str, pos: bool = True) -> None:
        if pos:
            log.error("{self.line}:{self.cursor-self.offset+1}:{self.path}:Lexer: {msg}", sep="")
        else:
            log.error("Lexer: {msg}", sep="")

    def advance(self, offset: int) -> None:
        for i in range(offset):
            self.curr_char = self.next_char
            if self.cursor+2 < len(self.text):
                self.next_char = self.text[self.cursor+2]
            else:
                self.next_char = None
            self.cursor += 1

    def range(self, index: int) -> bool:
        return index < len(self.text)

    def get_str(self, begin: int, end: int) -> str | None:
        if self.range(begin) and self.range(end):
            return self.text[begin:end]
        return None

    def digit(self, char: str | None = None) -> bool:
        if isinstance(char, str):
            return ord(char)>=ord('0') and ord(char)<=ord('9')
        return ord(self.curr_char)>=ord('0') and ord(self.curr_char)<=ord('9')

    def upper_case(self, char: str | None = None) -> bool:
        if isinstance(char, str):
            return ord(char)>=ord('A') and ord(char)<=ord('Z')
        return ord(self.curr_char)>=ord('A') and ord(self.curr_char)<=ord('Z')

    def lower_case(self, char: str | None = None) -> bool:
        if isinstance(char, str):
            return ord(char)>=ord('a') and ord(char)<=ord('z')
        return ord(self.curr_char)>=ord('a') and ord(self.curr_char)<=ord('z')
    
    def alpha(self, char: str | None = None) -> bool:
        return self.upper_case(char) or self.lower_case(char)
    
    def identifier_begin(self, char: str | None = None) -> bool:
        if isinstance(char, str):
            return char=='_' or self.alpha(char)
        return self.curr_char=='_' or self.alpha(char)

    def identifier_end(self, char: str | None = None) -> bool:
        return self.identifier_begin(char) or self.digit(char)

    def get_token(self) -> Token:
        # skip whitespaces and comments (` `, `\n`, `\r`, `\t`, `//`, `/*` and `*/`)
        while self.range(self.cursor):
            match (self.curr_char, self.next_char):
                case (' ' | '\n' | '\r' | '\t', _):
                    if self.curr_char == '\n':
                        self.line += 1
                        self.offset = self.cursor+1
                    self.advance(1)
                case ('/', '/'):
                    while self.range(self.cursor) and self.curr_char != '\n':
                        self.advance(1)
                case ('/', '*'):
                    self.advance(2)
                    while self.range(self.cursor+1) and self.curr_char != '*' and self.next_char != '/':
                        if self.get_char(self.cursor) == '\n':
                            self.line += 1
                            self.offset = self.cursor+1
                        self.advance(1)
                    self.advance(2)
                case _:
                    break

        # return early if end of file is reached
        if not self.range(self.cursor):
            return Token(TokenKind.eof, deepcopy(self.cursor), deepcopy(self.cursor), deepcopy(self.line), deepcopy(self.offset))
        
        begin: int = deepcopy(self.cursor)
        kind: int = TokenKind.undefined
        match (self.curr_char, self.next_char):
            case ('.', '.'):
                if self.range(self.cursor+1) and self.text[self.cursor+1] == '.':
                    self.advance(2)
                    kind = TokenKind.dotdotdot
            case (',', _): kind = TokenKind.comma
            case (':', _): kind = TokenKind.colon
            case (';', _): kind = TokenKind.semi_colon
            case ('@', _): kind = TokenKind.at
            case ('(', _): kind = TokenKind.open_paren
            case (')', _): kind = TokenKind.close_paren
            case ('{', _): kind = TokenKind.open_brace
            case ('}', _): kind = TokenKind.close_brace
            case _:
                if self.digit():
                    while self.range(self.cursor) and self.digit():
                        self.advance(1)
                    kind = TokenKind.integer
                elif self.identifier_begin():
                    while self.range(self.cursor+1) and self.identifier_end(self.text[self.cursor+1]):
                        self.advance(1)
                    kind = TokenKind.identifier
                    match self.text[begin:self.cursor+1]:
                        case "fn":
                            kind = TokenKind.function
                        case "return":
                            kind = TokenKind._return
                elif self.curr_char == '"':
                    self.advance(1)
                    while self.range(self.cursor) and self.curr_char != '"':
                        if self.curr_char == '\\':
                            self.advance(1)
                        self.advance(1)
                    kind = TokenKind.string
                else:
                    self.error("Encountered an invalid character (curr=0x%.2X, next=0x%.2X)!" % (ord(self.curr_char), ord(self.next_char)))

        self.advance(1)
        return Token(kind, begin, deepcopy(self.cursor), deepcopy(self.line), deepcopy(self.offset))

    def tokenise(self) -> list[Token]:
        tokens: list[Token] = []
        token: Token = self.get_token()

        while token.kind != TokenKind.eof:
            tokens.append(token)
            token = self.get_token()

        return tokens

class Parser:
    def __init__(self, lexer: Lexer) -> None:
        self.lexer:   Lexer       = lexer
        self.tokens:  list[Token] = lexer.tokenise()
        self.program: Program     = Program()
        self.index:   int         = 0

    def error(self, msg: str, token: Token | None = None, begin: bool = True) -> None:
        if begin and isinstance(token, Token):
            log.error(f"{token.line}:{token.begin-token.offset+1}:{self.lexer.path}: {msg}", sep="")
        elif not begin and isinstance(token, Token):
            log.error(f"{token.line}:{token.end-token.offset+1}:{self.lexer.path}: {msg}", sep="")

    def get_str(self, token: Token) -> str:
        return self.lexer.text[token.begin:token.end]

    def range(self, index: int) -> bool:
        return index < len(self.tokens)

    def get_function(self) -> FuncDefExpr | None:
        function: FuncDefExpr = FuncDefExpr()
        if self.tokens[self.cursor] != TokenKind.function:
            return None
        self.cursor += 1
        token: Token = self.tokens[self.cursor]
        function.name = self.get_str()
        return function
    
    def get_directive(self) -> None:
        if not self.range(self.index+1):
            token: Token = self.tokens[-1]
            self.error("Expected directive but reached end of file!", token)
        token: Token = self.tokens[self.index+1]
        match token:
            case TokenKind.indentifier:
                if not self.lexer.range(token.end-1):
                    self.error("Token has invalid range!", token)
                match self.get_str(token):
                    case "extern":
                        self.cursor += 2
                        function: FuncDefExpr | None = self.get_function()
                        if isinstance(function, FuncDefExpr):
                            self.program.extern.append(function)
                    case "entry":
                        self.cursor += 2
                        function: FuncDefExpr | None = self.get_function()
                        if isinstance(function, FuncDefExpr):
                            self.program.entry.append(function)
                    case _:
                        self.error(f"Invalide identifier `{self.get_str(token)}`!", token)
            case _:
                self.error(f"Expected directive of type `identifier` but found directive of type `{get_kind(TokenKind, token.kind)}`", token)

    def parse(self) -> Program:
        while self.range(self.index):
            token: Token = self.tokens[self.index]
            match token.kind:
                case TokenKind.at:
                    self.get_directive()
                case TokenKind.function:
                    self.get_function()
                case _:
                    log.error(f"Expected a token of kind `fn` or an `@` directive, but token of kind `{get_kind(TokenKind, token.kind)}`!", token)
        return self.program

def usage() -> None:
    log.print("USAGE: python mcc.py <run|com|lex|par> <input>")

def lex_tokens(lexer: Lexer) -> None:
    tokens: list[Token] = lexer.tokenise()
    length: int = 0
    for k in asdict(TokenKind()):
        if len(k) > length:
            length = len(k)
    for token in tokens:
        kind: str = get_kind(TokenKind, token.kind)
        kind += " " * (length - len(kind))
        text: str = lexer.text[token.begin:token.end]
        pos:  str = f"{token.line}:{token.begin-token.offset+1}:{lexer.path}:"
        log.print(f"Token:{pos} {kind} `{text}`!")

def parse_tokens(parser: Parser) -> None:
    program: Program = parser.parse()

def main() -> None:
    path: str = "hello.mcs"
    lexer: Lexer = Lexer(path)
    #lex_tokens(lexer)

    parser: Parser = Parser(lexer)
    parse_tokens(parser)
    
if __name__ == "__main__":
    main()
