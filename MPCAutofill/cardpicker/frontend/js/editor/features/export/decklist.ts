import {
  CardDocuments,
  ProjectMember,
  SlotProjectMembers,
} from "../../common/types";
import { Back, Card, Front, FaceSeparator } from "../../common/constants";
import { stripTextInParentheses } from "../../common/processing";

function extractProjectMemberNames(
  projectMembers: Array<SlotProjectMembers>,
  cardDocuments: CardDocuments
): Array<Array<string | null>> {
  /**
   * Retrieve the names of each card (note: excludes cardbacks and tokens) in the project.
   */

  function extractProjectMemberName(
    projectMember: ProjectMember | null
  ): string | null {
    return projectMember != null &&
      projectMember.selectedImage != null &&
      cardDocuments[projectMember.selectedImage] != null &&
      cardDocuments[projectMember.selectedImage].card_type === Card
      ? stripTextInParentheses(cardDocuments[projectMember.selectedImage].name)
      : null;
  }

  return projectMembers.map((slotProjectMembers: SlotProjectMembers) =>
    [Front, Back].flatMap((face) =>
      extractProjectMemberName(slotProjectMembers[face])
    )
  );
}

function stringifyCardNames(
  projectMemberNames: Array<Array<string | null>>
): Array<string> {
  /**
   * Convert each image's front and back names into a single string.
   * e.g. [["goblin", null], ["mountain", "island"]] => ["goblin", "mountain | island"]
   */

  return projectMemberNames
    .map((a: [string | null, string | null]) =>
      a[0] != null
        ? a[1] != null
          ? `${a[0]} ${FaceSeparator} ${a[1]}`
          : a[0]
        : ""
    )
    .filter((a) => a != null && a.length > 0);
}

function aggregateIntoQuantities(
  stringifiedCardNames: Array<string>
): Array<string> {
  /**
   * Count the occurrences of each item in `stringifiedCardNames` and prefix the item with its count.
   * e.g. ["goblin", "goblin"] => ["2x goblin"]
   */

  const aggregated: { [name: string]: number } = stringifiedCardNames.reduce(
    (accumulator: { [name: string]: number }, value) => {
      if (!Object.prototype.hasOwnProperty.call(accumulator, value)) {
        accumulator[value] = 0;
      }
      accumulator[value]++;
      return accumulator;
    },
    {}
  );
  return Object.keys(aggregated)
    .sort()
    .map((key: string) => `${aggregated[key]}x ${key}`);
}

export function generateDecklist(
  projectMembers: Array<SlotProjectMembers>,
  cardDocuments: CardDocuments
): Array<string> {
  /**
   * Generate a decklist representation of the project, suitable for uploading to deckbuilding websites
   * or sending to a friend. Only includes cards, not cardbacks or tokens.
   */

  const projectMemberNames = extractProjectMemberNames(
    projectMembers,
    cardDocuments
  );
  const stringifiedCardNames = stringifyCardNames(projectMemberNames);
  return aggregateIntoQuantities(stringifiedCardNames);
}
