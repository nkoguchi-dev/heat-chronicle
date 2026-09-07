/** Supplies the current instant; calendar interpretation belongs to the caller. */
export interface Clock {
  now(): Date;
}
