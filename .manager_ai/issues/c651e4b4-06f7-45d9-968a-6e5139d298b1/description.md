Errore abnorme:


Error executing tool get_issue_details: get_issue_details() got an unexpected keyword argument 'kwargs'

Ma la definizione del tool nel schema diceva che il solo parametro era kwargs. Quindi passavo kwargs: {"issue_id": "..."} ma il backend riceveva kwargs come argomento keyword invece di fare unpacking.

Tools con parametri espliciti funzionavano (es. list_credentials(project_id=...)), ma tutti quelli con firma **kwargs wrapper fallivano.