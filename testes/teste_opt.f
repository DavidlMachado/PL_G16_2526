PROGRAM TESTEOPT
    INTEGER X, Y, Z
    LOGICAL FLAG
    
    X = 2 + 3 * 2  ! Deve ser otimizado para X = 8 (Constant Folding)
    
    GOTO 100
    
    Y = 99         ! Deve ser removido (Dead Code)
    PRINT *, Y     ! Deve ser removido (Dead Code)
    
100 CONTINUE
    
    IF (.TRUE.) THEN
        Z = 1      ! O IF deve ser removido, esta linha mantida
    ELSE
        Z = 2      ! Este bloco ELSE deve ser removido
    ENDIF
    
    PRINT *, X, Z
END

INTEGER FUNCTION UNUSEDFUNC(A)
    INTEGER A
    UNUSEDFUNC = A * 2 ! Esta função inteira deve ser removida
    RETURN
END