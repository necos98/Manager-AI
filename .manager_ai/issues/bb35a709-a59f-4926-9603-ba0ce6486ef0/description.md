Memory cache inconsistente, lenta e bloccante.

Il nuovo sistema basato su file, rende il software un pachiderma, anche se viene effettuata la cache all'interno della memoria quest'ultima non serve a niente perché quando scade la cache deve essere ribuildato tutto e il software si pianta completamente.
Dobbiamo risolvere assolutamente questo aspetto, perché risulta inutilizzabile.

Il build dell'indice e della cache deve avvenire una volta sola e basta, ovvero all'apertura del software (come succede adesso)
Per il resto, la source of truth sarà appunto la memoria ram, cosi il retrive dei dati sarà sempre velocissimo.
Il flusso deve seguire: utente modifica => modifica la memoria ram => processo asyncrono aggiorna il file fisico.
Capito? La scrittura su disco deve essere asyncrona e non bloccante, la source of truth sarà sempre la memoria ram.
Analizza profondamente la mia richiesta e dammi delle soluzioni concrete al mio problema