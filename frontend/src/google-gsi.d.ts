declare namespace google.accounts.id {
  interface CredentialResponse {
    credential: string;
    select_by: string;
  }

  interface GsiButtonConfiguration {
    type: "standard" | "icon";
    theme?: "outline" | "filled_blue" | "filled_black";
    size?: "large" | "medium" | "small";
    text?: "signin_with" | "signup_with" | "continue_with" | "signin";
    shape?: "rectangular" | "pill" | "circle" | "square";
    width?: number;
  }

  function initialize(config: {
    client_id: string;
    callback: (response: CredentialResponse) => void;
    auto_select?: boolean;
  }): void;

  function renderButton(
    parent: HTMLElement,
    config: GsiButtonConfiguration
  ): void;

  function prompt(): void;
  function disableAutoSelect(): void;
}
