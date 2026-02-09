export interface Job {
    id: string;
    originalFilename: string;
    createdAt: string;
    status: 'STARTING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
    errorMessage?: string;
    fixStatus?: string;
    fixedFilePath?: string;
}

export interface Stats {
    label: string;
    value: string;
    trend: number;
    icon: any; // MUI Icon component
    status: 'primary' | 'success' | 'danger' | 'warning';
}
