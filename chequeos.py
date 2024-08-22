import cppcheck

@cppcheck.checker
def ternario(cfg, data):
    for tok in cfg.tokenlist:
        if tok.str == "?":
            mensaje = f"No esta permitido el uso del operador ternario '?:'."
            cppcheck.reportError(tok, 'error', mensaje)


@cppcheck.checker
def lazos(cfg, data):
    for tok in cfg.tokenlist:
        for prohibido in ["break", "continue"]:
            if tok.str == prohibido:
                mensaje = f"No esta permitido el uso de la manipulación de lazo {prohibido}."
                cppcheck.reportError(tok, 'error', mensaje)


@cppcheck.checker
def compuesto(cfg, data):
    for tok in cfg.tokenlist:
        for prohibido in ["/=","+=","-=","%=","*="]:
            if tok.str == prohibido:
                mensaje = f"No se recomienda el uso de operadores compuestos ({prohibido})."
                cppcheck.reportError(tok, 'warn', mensaje)

@cppcheck.checker
def retornos(cfg, data):
    for func in cfg.functions:
        return_count = 0
        pila = []
        token = func.token

        while token:
            if token.str == "return":
                return_count += 1
            
            if (token.str == "{"):
                pila.append(token.str)

            if (token.str == "}"):
                pila.pop()
                if(len(pila) == 0):
                    break

            token = token.next

        if return_count > 1:
            mensaje = f"La función '{func.name}' tiene multiples return ({return_count})."
            cppcheck.reportError(func.token, 'error', mensaje)
