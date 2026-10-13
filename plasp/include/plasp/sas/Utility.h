#ifndef __PLASP__SAS__UTILITY_H
#define __PLASP__SAS__UTILITY_H

#include <vector>

#include <tokenize/Tokenizer.h>

#include <plasp/sas/AssignedVariable.h>

namespace plasp
{
namespace sas
{

////////////////////////////////////////////////////////////////////////////////////////////////////
//
// Utility
//
////////////////////////////////////////////////////////////////////////////////////////////////////

struct UtilityFact
{
  AssignedVariable fact;
  int weight;
};

using UtilityFacts = std::vector<UtilityFact>;

class Utility
{
	public:
		static Utility fromSAS(tokenize::Tokenizer<> &tokenizer, const Variables &variables);

	public:
		const UtilityFacts &facts() const;

	private:
		Utility() = default;

		UtilityFacts m_facts;
};

////////////////////////////////////////////////////////////////////////////////////////////////////

}
}

#endif
