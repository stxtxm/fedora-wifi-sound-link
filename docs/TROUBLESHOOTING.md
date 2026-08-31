# Troubleshooting

## Craquements même en Opus
Passer en ROC Stable. Vérifier `pw-top` quantum: doit être 1024. Si crack, augmenter `--latency` à 500ms.

## Saccades wifi
`ss -una | grep 4711` vérifier drops. Passer Opus 192k (8x moins de bande) ou Roc FEC.

## Latence
Stable 300-600ms normal. Fast 60ms pour gaming mais moins stable.
