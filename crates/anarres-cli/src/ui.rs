use std::fmt;
use std::io::Write;

use anstyle::{AnsiColor, Color, Style};

const ACCENT: Style = Style::new()
    .fg_color(Some(Color::Ansi(AnsiColor::Cyan)))
    .bold();
const SUCCESS: Style = Style::new()
    .fg_color(Some(Color::Ansi(AnsiColor::Green)))
    .bold();
const WARNING: Style = Style::new()
    .fg_color(Some(Color::Ansi(AnsiColor::Yellow)))
    .bold();
const ERROR: Style = Style::new()
    .fg_color(Some(Color::Ansi(AnsiColor::Red)))
    .bold();
const LABEL: Style = Style::new().bold();
const MUTED: Style = Style::new().dimmed();

pub(crate) fn configure(choice: anstream::ColorChoice) {
    choice.write_global();
}

pub(crate) fn line(arguments: fmt::Arguments<'_>) {
    let mut stream = anstream::stdout().lock();
    let _ = writeln!(stream, "{arguments}");
}

pub(crate) fn blank() {
    line(format_args!(""));
}

pub(crate) fn title(value: &str) {
    line(format_args!("{ACCENT}{value}{ACCENT:#}"));
}

pub(crate) fn success(label: &str, value: impl fmt::Display) {
    line(format_args!("  {SUCCESS}✓ {label:<12}{SUCCESS:#} {value}"));
}

pub(crate) fn warning(label: &str, value: impl fmt::Display) {
    line(format_args!("  {WARNING}! {label:<12}{WARNING:#} {value}"));
}

pub(crate) fn field(label: &str, value: impl fmt::Display) {
    line(format_args!("    {LABEL}{label:<18}{LABEL:#} {value}"));
}

pub(crate) fn muted(value: impl fmt::Display) {
    line(format_args!("    {MUTED}{value}{MUTED:#}"));
}

pub(crate) fn next(command: &str) {
    blank();
    line(format_args!("{ACCENT}Next{ACCENT:#}  {command}"));
}

pub(crate) fn error(value: impl fmt::Display) {
    let rendered = value.to_string();
    let (message, hint) = match rendered.split_once("\nhint: ") {
        Some((message, hint)) => (message, Some(hint)),
        None => (rendered.as_str(), None),
    };
    let mut stream = anstream::stderr().lock();
    let _ = writeln!(stream, "{ERROR}error:{ERROR:#} {message}");
    if let Some(hint) = hint {
        let _ = writeln!(stream, "  {ACCENT}hint:{ACCENT:#} {hint}");
    }
}

pub(crate) fn warning_stderr(value: impl fmt::Display) {
    let mut stream = anstream::stderr().lock();
    let _ = writeln!(stream, "{WARNING}warning:{WARNING:#} {value}");
}
