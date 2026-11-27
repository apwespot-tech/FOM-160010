export type FieldErrors = Record<string, string>;

export interface ValidationErrorItem {
    type: string;
    loc: Array<string | number>;
    msg: string;
}

export interface ApiErrorBody {
    code: string;
    detail: string | ValidationErrorItem[];
}

export interface UserBody {
    id: number;
    username: string;
    time_zone: string;
}

export interface User {
    id: number;
    username: string;
    timeZone: string;
}
