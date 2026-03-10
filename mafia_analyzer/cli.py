"""CLI entrypoint for mafia game analyzer."""

from __future__ import annotations

from pathlib import Path

import click

from mafia_analyzer.audio import extract_audio
from mafia_analyzer.summarize import summarize
from mafia_analyzer.transcribe import transcribe


@click.command()
@click.argument("video_url")
@click.option("--language", "-l", default="ru", help="Language code for transcription (default: ru).")
@click.option("--output", "-o", default=None, help="Output file for the report (default: stdout).")
@click.option("--keep-audio", is_flag=True, help="Keep downloaded audio file after processing.")
@click.option("--transcript-out", default=None, help="Save raw transcript to this file.")
def main(
    video_url: str,
    language: str,
    output: str | None,
    keep_audio: bool,
    transcript_out: str | None,
) -> None:
    """Analyze a mafia game video.

    VIDEO_URL is a link to the game video (YouTube, Twitch, etc.).
    """
    # Step 1: Extract audio
    click.echo("Step 1/3: Extracting audio from video...")
    audio_path = extract_audio(video_url)
    click.echo(f"  Audio saved to {audio_path}")

    try:
        # Step 2: Transcribe with diarization
        click.echo("Step 2/3: Transcribing audio with speaker diarization...")
        transcript = transcribe(audio_path, language_code=language)
        click.echo(f"  Got {len(transcript.utterances)} utterances")

        if transcript_out:
            Path(transcript_out).write_text(transcript.as_dialogue(), encoding="utf-8")
            click.echo(f"  Transcript saved to {transcript_out}")

        # Step 3: Summarize
        click.echo("Step 3/3: Generating game analysis...")

        def _ask_user(questions: str) -> str:
            click.echo("\nThe analyzer needs some clarification:\n")
            click.echo(questions)
            click.echo()
            return click.prompt("Your answer")

        report = summarize(transcript, ask_fn=_ask_user)

        if output:
            Path(output).write_text(report, encoding="utf-8")
            click.echo(f"Report saved to {output}")
        else:
            click.echo("\n" + "=" * 60)
            click.echo(report)
    finally:
        if not keep_audio:
            audio_path.unlink(missing_ok=True)
            audio_path.parent.rmdir()


if __name__ == "__main__":
    main()
