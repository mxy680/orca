/*
  Warnings:

  - You are about to drop the column `is_default` on the `Team` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "Team" DROP COLUMN "is_default",
ADD COLUMN     "isDefault" BOOLEAN NOT NULL DEFAULT true;
