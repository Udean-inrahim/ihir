document.addEventListener("DOMContentLoaded", () => {
  document.querySelector("[data-error-summary]")?.focus();
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
});
