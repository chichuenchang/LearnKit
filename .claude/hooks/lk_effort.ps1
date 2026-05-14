$d = $Input | Out-String | ConvertFrom-Json
$p = if ($d.prompt) { $d.prompt } else { "" }

if ($p -match '(?i)^\s*/lkingest') {
    @{
        hookSpecificOutput = @{
            hookEventName     = "UserPromptSubmit"
            additionalContext = "LEARNKIT EFFORT: MAXIMUM. /lkingest active. Use full extended thinking to carefully extract, classify, and generate study content."
        }
    } | ConvertTo-Json -Compress
} elseif ($p -match '(?i)^\s*/lkquiz') {
    @{
        hookSpecificOutput = @{
            hookEventName     = "UserPromptSubmit"
            additionalContext = "LEARNKIT EFFORT: MEDIUM. /lkquiz active. Use moderate reasoning to generate well-calibrated quiz questions and evaluate answers accurately."
        }
    } | ConvertTo-Json -Compress
} elseif ($p -match '(?i)^\s*/lksave') {
    @{
        hookSpecificOutput = @{
            hookEventName     = "UserPromptSubmit"
            additionalContext = "LEARNKIT EFFORT: MEDIUM. /lksave active. Carefully review session context to find and recover any missed data writes."
        }
    } | ConvertTo-Json -Compress
} elseif ($p -match '(?i)^\s*/lksetup') {
    @{
        hookSpecificOutput = @{
            hookEventName     = "UserPromptSubmit"
            additionalContext = "LEARNKIT EFFORT: MEDIUM. /lksetup active. Carefully detect Python environment and configure paths."
        }
    } | ConvertTo-Json -Compress
} elseif ($p -match '(?i)^\s*/lk') {
    @{
        hookSpecificOutput = @{
            hookEventName     = "UserPromptSubmit"
            additionalContext = "LEARNKIT EFFORT: MINIMAL. /lk command active. Execute directly, no extended reasoning needed."
        }
    } | ConvertTo-Json -Compress
}
