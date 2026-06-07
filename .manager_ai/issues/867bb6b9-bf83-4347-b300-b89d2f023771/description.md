29. $issueId.tsx — 324 righe, 6 renderizzazioni duplicate di TerminalWithQuestions

  Componente monolite che gestisce terminali, pipeline, issue detail, domande, dialog. Blocco pendingQuestions duplicato
   3 volte.
  Fix: Estrarre TerminalPanel, PipelinePanel, PendingQuestionsSection, hook useTerminalLayout.