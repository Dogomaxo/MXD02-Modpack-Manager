---
name: "\U0001F41E Bug report"
about: Crea un reporte para ayudarnos a mejorar.
title: "[BUG]"
labels: bug
assignees: Dogomaxo

---

body:
  - type: markdown
    attributes:
      value: >
        Gracias por tomarte el tiempo de reportar un bug. Por favor, completa toda la información posible.
        Esto nos ayudará a identificar el problema con mayor rapidez.

  - type: input
    id: what-happened
    attributes:
      label: "¿Qué sucedió?"
      description: "Describe el comportamiento inesperado."
      placeholder: "Ejemplo: El instalador se cierra al iniciar..."
    validations:
      required: true

  - type: input
    id: steps-to-reproduce
    attributes:
      label: "Pasos para reproducirlo"
      description: "Proporciona una secuencia clara de pasos."
      placeholder: "1. ... \n2. ... \n3. ..."
    validations:
      required: true

  - type: dropdown
    id: affected-version
    attributes:
      label: "Versión afectada"
      description: "¿En qué versión ocurre el bug?"
      options:
        - "v1.0"
        - "v1.1"
        - "v1.2"
        - "Otra"
    validations:
      required: true

  - type: textarea
    id: additional-context
    attributes:
      label: "Información adicional"
      description: "Logs, capturas de pantalla, configuraciones, etc."
      placeholder: "Agrega cualquier detalle extra que consideres relevante."
