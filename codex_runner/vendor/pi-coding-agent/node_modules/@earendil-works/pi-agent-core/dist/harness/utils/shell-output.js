import { ExecutionError, err, ok, toError } from "../types.js";
import { DEFAULT_MAX_BYTES, DEFAULT_MAX_LINES, truncateTail } from "./truncate.js";
function toExecutionError(error) {
    if (error instanceof ExecutionError)
        return error;
    const cause = toError(error);
    return new ExecutionError("unknown", cause.message, cause);
}
export function sanitizeBinaryOutput(str) {
    return Array.from(str)
        .filter((char) => {
        const code = char.codePointAt(0);
        if (code === undefined)
            return false;
        if (code === 0x09 || code === 0x0a || code === 0x0d)
            return true;
        if (code <= 0x1f)
            return false;
        if (code >= 0xfff9 && code <= 0xfffb)
            return false;
        return true;
    })
        .join("");
}
function trimToLastUtf8Bytes(text, maxBytes, encoder) {
    const bytes = encoder.encode(text);
    if (bytes.byteLength <= maxBytes)
        return text;
    let start = bytes.byteLength - maxBytes;
    while (start < bytes.byteLength && ((bytes[start] ?? 0) & 0xc0) === 0x80)
        start++;
    return new TextDecoder().decode(bytes.subarray(start));
}
export async function executeShellWithCapture(env, command, options) {
    let tailOutput = "";
    const maxOutputBytes = DEFAULT_MAX_BYTES * 2;
    const encoder = new TextEncoder();
    let totalBytes = 0;
    let completedLines = 0;
    let hasOpenLine = false;
    let currentLineBytes = 0;
    let fullOutputPath;
    let fullOutputRequested = false;
    let acceptingOutput = true;
    let writeChain = Promise.resolve(ok(undefined));
    let captureError;
    const appendFullOutput = (text) => {
        if (!fullOutputRequested || captureError)
            return;
        writeChain = writeChain.then(async (previous) => {
            if (!previous.ok)
                return previous;
            if (!fullOutputPath)
                return err(new ExecutionError("unknown", "Full output path was not created"));
            const appendResult = await env.appendFile(fullOutputPath, text);
            return appendResult.ok ? ok(undefined) : err(toExecutionError(appendResult.error));
        });
    };
    const ensureFullOutputFile = (initialContent) => {
        if (fullOutputRequested || captureError)
            return;
        fullOutputRequested = true;
        writeChain = writeChain.then(async (previous) => {
            if (!previous.ok)
                return previous;
            const tempFile = await env.createTempFile({ prefix: "bash-", suffix: ".log" });
            if (!tempFile.ok)
                return err(toExecutionError(tempFile.error));
            fullOutputPath = tempFile.value;
            const appendResult = await env.appendFile(tempFile.value, initialContent);
            return appendResult.ok ? ok(undefined) : err(toExecutionError(appendResult.error));
        });
    };
    const createProgress = () => {
        const tailTruncation = truncateTail(tailOutput);
        const totalLines = completedLines + (hasOpenLine ? 1 : 0);
        const truncated = totalLines > DEFAULT_MAX_LINES || totalBytes > DEFAULT_MAX_BYTES;
        const truncation = {
            ...tailTruncation,
            truncated,
            truncatedBy: truncated
                ? (tailTruncation.truncatedBy ?? (totalBytes > DEFAULT_MAX_BYTES ? "bytes" : "lines"))
                : null,
            totalLines,
            totalBytes,
        };
        return {
            output: truncated ? truncation.content : tailOutput,
            truncation,
            fullOutputPath,
            lastLineBytes: currentLineBytes,
        };
    };
    const onChunk = (chunk) => {
        if (!acceptingOutput)
            return;
        try {
            const text = sanitizeBinaryOutput(chunk).replace(/\r/g, "");
            const textBytes = encoder.encode(text).byteLength;
            totalBytes += textBytes;
            const newlineCount = text.split("\n").length - 1;
            completedLines += newlineCount;
            const lastNewline = text.lastIndexOf("\n");
            if (lastNewline >= 0) {
                const trailingText = text.slice(lastNewline + 1);
                currentLineBytes = encoder.encode(trailingText).byteLength;
                hasOpenLine = trailingText.length > 0;
            }
            else if (text.length > 0) {
                currentLineBytes += textBytes;
                hasOpenLine = true;
            }
            tailOutput += text;
            const totalLines = completedLines + (hasOpenLine ? 1 : 0);
            if ((totalBytes > DEFAULT_MAX_BYTES || totalLines > DEFAULT_MAX_LINES) && !fullOutputRequested) {
                ensureFullOutputFile(tailOutput);
            }
            else if (fullOutputRequested) {
                appendFullOutput(text);
            }
            tailOutput = trimToLastUtf8Bytes(tailOutput, maxOutputBytes, encoder);
            options?.onChunk?.(text, createProgress);
        }
        catch (error) {
            captureError = toExecutionError(error);
        }
    };
    try {
        const result = await env.exec(command, {
            cwd: options?.cwd,
            env: options?.env,
            inheritEnv: options?.inheritEnv,
            timeout: options?.timeout,
            abortSignal: options?.abortSignal,
            onStdout: onChunk,
            onStderr: onChunk,
        });
        acceptingOutput = false;
        let progress = createProgress();
        if (progress.truncation.truncated && !fullOutputRequested)
            ensureFullOutputFile(tailOutput);
        const writeResult = await writeChain;
        if (!writeResult.ok)
            return err(writeResult.error);
        if (captureError)
            return err(captureError);
        progress = createProgress();
        if (!result.ok) {
            if (result.error.code === "aborted" || options?.abortSignal?.aborted) {
                return ok({
                    ...progress,
                    exitCode: undefined,
                    cancelled: true,
                    truncated: progress.truncation.truncated,
                });
            }
            if (options?.returnExecutionErrors) {
                return ok({
                    ...progress,
                    exitCode: undefined,
                    cancelled: false,
                    truncated: progress.truncation.truncated,
                    executionError: result.error,
                });
            }
            return err(result.error);
        }
        const cancelled = options?.abortSignal?.aborted ?? false;
        return ok({
            ...progress,
            exitCode: cancelled ? undefined : result.value.exitCode,
            cancelled,
            truncated: progress.truncation.truncated,
        });
    }
    catch (error) {
        acceptingOutput = false;
        return err(toExecutionError(error));
    }
}
//# sourceMappingURL=shell-output.js.map