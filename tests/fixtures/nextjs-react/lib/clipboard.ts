// Synthetic fixture — toast claims success even when writeText rejected.

export async function copyWithToast(text: string, toast: (msg: string) => void) {
  navigator.clipboard.writeText(text).catch(() => {
    // HIGH: toast-in-catch — we tell the user "copied" but the copy failed.
    toast("copied");
  });
}
